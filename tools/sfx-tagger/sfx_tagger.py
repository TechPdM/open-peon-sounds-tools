#!/usr/bin/env python3
"""sfx-tagger: Categorise short UI sound effects across 8 dimensions.

Tags each file with: sentiment, duration, loudness, intensity, pitch,
envelope, tonality, and sound type.

Usage:
    python3 sfx_tagger.py ./sounds/*.wav --out tags.json
    python3 sfx_tagger.py file1.wav file2.wav --short-threshold 0.2 --long-threshold 1.0
"""

import argparse
import json
import os
import sys
import warnings

import librosa
import numpy as np

warnings.filterwarnings("ignore", message="n_fft=.*is too large")


# ── Feature extraction ──────────────────────────────────────────────


def extract_features(path, sr=22050):
    """Extract audio features from a WAV file. Returns a dict of raw feature values."""
    y, sr = librosa.load(path, sr=sr)
    hop_length = 512

    duration = librosa.get_duration(y=y, sr=sr)

    # RMS energy
    rms = librosa.feature.rms(y=y)[0]
    mean_rms = float(np.mean(rms))
    peak = float(np.max(np.abs(y))) if len(y) > 0 else 0.0
    crest_factor = peak / mean_rms if mean_rms > 0 else 0.0
    rms_db = 20 * np.log10(mean_rms) if mean_rms > 0 else -80.0

    # Attack time: time from start to peak RMS frame
    if len(rms) > 0:
        peak_frame = int(np.argmax(rms))
        attack_time = float(peak_frame * hop_length / sr)
    else:
        peak_frame = 0
        attack_time = 0.0

    # Decay time: time from peak RMS to where RMS drops to 10% of peak RMS
    # (relative threshold avoids the -40dB absolute threshold problem where
    # quiet sounds appear to have no decay)
    if len(rms) > 0 and peak_frame < len(rms) - 1:
        peak_rms = rms[peak_frame]
        decay_threshold = peak_rms * 0.1  # -20dB relative to peak
        tail = rms[peak_frame:]
        below = np.where(tail < decay_threshold)[0]
        if len(below) > 0:
            decay_frames = int(below[0])
        else:
            decay_frames = len(tail)
        decay_time = float(decay_frames * hop_length / sr)
    else:
        decay_time = 0.0

    # Spectral centroid
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    mean_centroid = float(np.mean(centroid))

    # Spectral rolloff
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    mean_rolloff = float(np.mean(rolloff))

    # Spectral bandwidth
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    mean_bandwidth = float(np.mean(bandwidth))

    # Spectral flatness
    flatness = librosa.feature.spectral_flatness(y=y)[0]
    mean_flatness = float(np.mean(flatness))

    # Zero-crossing rate
    zcr = librosa.feature.zero_crossing_rate(y=y)[0]
    mean_zcr = float(np.mean(zcr))

    # Centroid slope (pitch direction over time)
    # Only computed over non-silent frames to avoid silence at the tail
    # dragging the slope negative
    if len(centroid) > 1 and len(rms) > 1:
        rms_threshold = np.max(rms) * 0.05
        active_mask = rms[:len(centroid)] > rms_threshold
        active_centroid = centroid[active_mask]
        if len(active_centroid) > 2:
            frames = np.arange(len(active_centroid))
            coeffs = np.polyfit(frames, active_centroid, 1)
            centroid_slope = float(coeffs[0])
        else:
            centroid_slope = 0.0
    else:
        centroid_slope = 0.0

    # Fundamental frequency via pyin
    # Guard against very short signals where pyin can fail
    if len(y) > 2048:
        f0, voiced_flag, _ = librosa.pyin(y, fmin=80, fmax=4000, sr=sr)
        if voiced_flag is not None:
            voiced_f0 = f0[voiced_flag]
        else:
            voiced_f0 = np.array([])
        if len(voiced_f0) > 0:
            fundamental_freq = float(np.median(voiced_f0))
        else:
            fundamental_freq = mean_centroid
    else:
        fundamental_freq = mean_centroid

    # Harmonic ratio — use spectral flatness as a more reliable tonality
    # indicator for synthesised sounds, where harmonic/percussive separation
    # can fail. We keep the HPSS ratio but also compute an autocorrelation-
    # based periodicity measure.
    if len(y) > 2048:
        y_harmonic = librosa.effects.harmonic(y=y)
        total_energy = float(np.sum(y ** 2))
        harmonic_energy = float(np.sum(y_harmonic ** 2))
        harmonic_ratio = harmonic_energy / total_energy if total_energy > 0 else 0.0
    else:
        harmonic_ratio = 0.0

    # Autocorrelation periodicity: how periodic/tonal the signal is
    # This catches synthesised tonal sounds that HPSS misclassifies
    if len(y) > 2048:
        autocorr = librosa.autocorrelate(y, max_size=sr // 80)
        if len(autocorr) > 1 and autocorr[0] > 0:
            # Normalise and find strongest peak after lag 0
            autocorr_norm = autocorr / autocorr[0]
            # Skip the first few lags (too close to lag 0)
            min_lag = sr // 4000  # ~5.5 samples at 22050
            if min_lag < len(autocorr_norm):
                peak_autocorr = float(np.max(autocorr_norm[min_lag:]))
            else:
                peak_autocorr = 0.0
        else:
            peak_autocorr = 0.0
    else:
        peak_autocorr = 0.0

    # Onset count
    if len(y) > 2048:
        onsets = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length)
        onset_count = int(len(onsets))
    else:
        onset_count = 1

    return {
        "duration": duration,
        "rms_db": rms_db,
        "crest_factor": crest_factor,
        "attack_time": attack_time,
        "decay_time": decay_time,
        "spectral_centroid": mean_centroid,
        "spectral_rolloff": mean_rolloff,
        "spectral_bandwidth": mean_bandwidth,
        "spectral_flatness": mean_flatness,
        "zcr": mean_zcr,
        "centroid_slope": centroid_slope,
        "fundamental_freq": fundamental_freq,
        "harmonic_ratio": harmonic_ratio,
        "peak_autocorr": peak_autocorr,
        "onset_count": onset_count,
    }


# ── Rule-based classifiers ──────────────────────────────────────────


def classify_sentiment(features):
    """Positive/negative/neutral based on spectral brightness and pitch direction."""
    score = 0.0

    centroid = features["spectral_centroid"]
    if centroid > 3000:
        score += 1
    elif centroid < 1500:
        score -= 1

    rolloff = features["spectral_rolloff"]
    if rolloff > 6000:
        score += 0.5
    elif rolloff < 3000:
        score -= 0.5

    slope = features["centroid_slope"]
    if slope > 5:
        score += 1
    elif slope < -5:
        score -= 1

    if score >= 1:
        return "positive"
    elif score <= -1:
        return "negative"
    return "neutral"


def classify_duration(features, short_thresh, long_thresh):
    d = features["duration"]
    if d < short_thresh:
        return "short"
    elif d > long_thresh:
        return "long"
    return "medium"


def classify_loudness(features, quiet_thresh, loud_thresh):
    db = features["rms_db"]
    if db < quiet_thresh:
        return "quiet"
    elif db > loud_thresh:
        return "loud"
    return "medium"


def classify_intensity(features):
    """Composite score from crest factor, attack time, and ZCR."""
    score = 0.0

    if features["crest_factor"] > 8:
        score += 1
    elif features["crest_factor"] < 4:
        score -= 1

    if features["attack_time"] < 0.02:
        score += 1
    elif features["attack_time"] > 0.1:
        score -= 1

    if features["zcr"] > 0.15:
        score += 1
    elif features["zcr"] < 0.05:
        score -= 1

    if score >= 1.5:
        return "intense"
    elif score <= -1.5:
        return "soft"
    return "medium"


def classify_pitch(features):
    """Low/mid/high based on fundamental frequency."""
    freq = features["fundamental_freq"]
    if freq < 300:
        return "low"
    elif freq > 2000:
        return "high"
    return "mid"


def classify_envelope(features):
    """Percussive/sustained/swelling/decaying based on temporal energy shape."""
    duration = features["duration"]
    attack = features["attack_time"]
    decay = features["decay_time"]

    if duration <= 0:
        return "percussive"

    attack_ratio = attack / duration
    decay_ratio = decay / duration

    # Swelling: most of the sound is the attack phase
    if attack_ratio > 0.5:
        return "swelling"

    # Percussive: fast attack and short decay
    if attack < 0.02 and decay_ratio < 0.3:
        return "percussive"

    # Decaying: fast attack, long tail
    if attack_ratio < 0.2 and decay_ratio > 0.5:
        return "decaying"

    return "sustained"


def classify_tonality(features):
    """Tonal/noisy using autocorrelation periodicity and spectral flatness.

    HPSS-based harmonic ratio is unreliable for many synthesised UI sounds,
    so we primarily use autocorrelation (is there a repeating period?) and
    spectral flatness (is the spectrum peaked or flat?).
    """
    autocorr = features["peak_autocorr"]
    flatness = features["spectral_flatness"]
    harmonic = features["harmonic_ratio"]

    # Strong autocorrelation = definitely periodic/tonal
    if autocorr > 0.5:
        return "tonal"

    # Very flat spectrum = definitely noisy
    if flatness > 0.5:
        return "noisy"

    # Low flatness (peaked spectrum) suggests tonal content
    if flatness < 0.15:
        return "tonal"

    # HPSS agrees it's harmonic
    if harmonic > 0.5 and flatness < 0.3:
        return "tonal"

    # Moderate autocorrelation + moderate flatness = probably tonal
    if autocorr > 0.3 and flatness < 0.3:
        return "tonal"

    return "noisy"


def classify_type(features):
    """Heuristic sound type classification. Priority-ordered, first match wins."""
    duration = features["duration"]
    flatness = features["spectral_flatness"]
    centroid = features["spectral_centroid"]
    zcr = features["zcr"]
    slope = features["centroid_slope"]
    freq = features["fundamental_freq"]
    attack = features["attack_time"]
    decay = features["decay_time"]
    autocorr = features["peak_autocorr"]

    is_tonal = (autocorr > 0.5) or (flatness < 0.15) or (autocorr > 0.3 and flatness < 0.3)
    is_noisy = not is_tonal
    is_percussive = attack < 0.02
    has_strong_slope = abs(slope) > 50

    # Click: very short, percussive, broadband
    if duration < 0.05 and is_percussive and flatness > 0.1:
        return "click"

    # Thud: percussive, low pitch, dark
    if is_percussive and freq < 300 and centroid < 1500:
        return "thud"

    # Buzz: noisy, sustained-ish, harsh, mid-low pitch
    if is_noisy and zcr > 0.1 and duration > 0.1 and freq < 2000:
        return "buzz"

    # Whoosh: noisy, strong slope, medium-long
    if is_noisy and has_strong_slope and duration > 0.15:
        return "whoosh"

    # Sweep: strong slope, medium-long (tonal or noisy)
    if has_strong_slope and duration > 0.15:
        return "sweep"

    # Chime: tonal, mid-high pitch, decaying envelope
    if is_tonal and freq > 500 and duration > 0 and decay / duration > 0.4:
        return "chime"

    # Beep: tonal fallback
    if is_tonal:
        return "beep"

    return "beep"


def classify(features, short_thresh, long_thresh, quiet_thresh, loud_thresh):
    """Return a dict of tagged categories for a single file."""
    return {
        "sentiment": classify_sentiment(features),
        "duration": classify_duration(features, short_thresh, long_thresh),
        "loudness": classify_loudness(features, quiet_thresh, loud_thresh),
        "intensity": classify_intensity(features),
        "pitch": classify_pitch(features),
        "envelope": classify_envelope(features),
        "tonality": classify_tonality(features),
        "type": classify_type(features),
    }


# ── CLI ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Tag short UI sound effects across 8 dimensions."
    )
    parser.add_argument("files", nargs="+", help="WAV files to analyse")
    parser.add_argument("--out", "-o", default=None, help="Output JSON file (default: tags.json in same directory as input files)")
    parser.add_argument("--short-threshold", type=float, default=0.25, help="Duration below this is 'short' (seconds)")
    parser.add_argument("--long-threshold", type=float, default=0.8, help="Duration above this is 'long' (seconds)")
    parser.add_argument("--loud-threshold", type=float, default=-16, help="RMS dB above this is 'loud'")
    parser.add_argument("--quiet-threshold", type=float, default=-28, help="RMS dB below this is 'quiet'")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print raw features alongside tags")

    args = parser.parse_args()

    results = {}
    for filepath in args.files:
        if not os.path.isfile(filepath):
            print(f"warning: skipping {filepath} (not found)", file=sys.stderr)
            continue

        name = os.path.basename(filepath)
        try:
            features = extract_features(filepath)
        except Exception as e:
            print(f"warning: skipping {name}: {e}", file=sys.stderr)
            continue

        tags = classify(features, args.short_threshold, args.long_threshold,
                        args.quiet_threshold, args.loud_threshold)

        if args.verbose:
            results[name] = {"tags": tags, "features": features}
        else:
            results[name] = tags

    output = json.dumps(results, indent=2)

    # Default output path: tags.json in the same directory as the first input file
    out_path = args.out
    if out_path is None:
        first_file = next((f for f in args.files if os.path.isfile(f)), None)
        if first_file:
            out_path = os.path.join(os.path.dirname(os.path.abspath(first_file)), "tags.json")
        else:
            print(output)
            return

    with open(out_path, "w") as f:
        f.write(output + "\n")
    print(f"wrote {len(results)} entries to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
