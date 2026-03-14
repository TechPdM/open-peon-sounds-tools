#!/usr/bin/env python3
"""sfx-tagger: Categorise short UI sound effects by sentiment, duration, loudness, and intensity.

Usage:
    python3 sfx_tagger.py ./sounds/*.wav --out tags.json
    python3 sfx_tagger.py file1.wav file2.wav --short-threshold 0.2 --long-threshold 1.0
"""

import argparse
import json
import os
import sys

import librosa
import numpy as np


# ── Feature extraction ──────────────────────────────────────────────


def extract_features(path, sr=22050):
    """Extract audio features from a WAV file. Returns a dict of raw feature values."""
    y, sr = librosa.load(path, sr=sr)

    duration = librosa.get_duration(y=y, sr=sr)

    rms = librosa.feature.rms(y=y)[0]
    mean_rms = float(np.mean(rms))
    peak = float(np.max(np.abs(y))) if len(y) > 0 else 0.0
    crest_factor = peak / mean_rms if mean_rms > 0 else 0.0

    # RMS in dB (approximation of loudness)
    rms_db = 20 * np.log10(mean_rms) if mean_rms > 0 else -80.0

    # Attack time: time from start to peak RMS frame
    if len(rms) > 0:
        peak_frame = int(np.argmax(rms))
        hop_length = 512  # librosa default
        attack_time = float(peak_frame * hop_length / sr)
    else:
        attack_time = 0.0

    # Spectral centroid (mean, in Hz)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    mean_centroid = float(np.mean(centroid))

    # Spectral rolloff (mean, in Hz)
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    mean_rolloff = float(np.mean(rolloff))

    # Zero-crossing rate (mean)
    zcr = librosa.feature.zero_crossing_rate(y=y)[0]
    mean_zcr = float(np.mean(zcr))

    # Pitch direction: slope of spectral centroid over time
    if len(centroid) > 1:
        frames = np.arange(len(centroid))
        coeffs = np.polyfit(frames, centroid, 1)
        centroid_slope = float(coeffs[0])
    else:
        centroid_slope = 0.0

    return {
        "duration": duration,
        "rms_db": rms_db,
        "crest_factor": crest_factor,
        "attack_time": attack_time,
        "spectral_centroid": mean_centroid,
        "spectral_rolloff": mean_rolloff,
        "zcr": mean_zcr,
        "centroid_slope": centroid_slope,
    }


# ── Rule-based classifier ───────────────────────────────────────────


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

    # High crest factor = sharp transient = intense
    if features["crest_factor"] > 8:
        score += 1
    elif features["crest_factor"] < 4:
        score -= 1

    # Fast attack = intense
    if features["attack_time"] < 0.02:
        score += 1
    elif features["attack_time"] > 0.1:
        score -= 1

    # High ZCR = harsh/buzzy = intense
    if features["zcr"] > 0.15:
        score += 1
    elif features["zcr"] < 0.05:
        score -= 1

    if score >= 1.5:
        return "intense"
    elif score <= -1.5:
        return "soft"
    return "medium"


def classify_sentiment(features):
    """Positive/negative/neutral based on spectral brightness and pitch direction."""
    score = 0.0

    # Bright centroid → positive, dark → negative
    centroid = features["spectral_centroid"]
    if centroid > 3000:
        score += 1
    elif centroid < 1500:
        score -= 1

    # High rolloff → brighter energy distribution → positive
    rolloff = features["spectral_rolloff"]
    if rolloff > 6000:
        score += 0.5
    elif rolloff < 3000:
        score -= 0.5

    # Rising pitch → positive, falling → negative
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


def classify(features, short_thresh, long_thresh, quiet_thresh, loud_thresh):
    """Return a dict of tagged categories for a single file."""
    return {
        "sentiment": classify_sentiment(features),
        "duration": classify_duration(features, short_thresh, long_thresh),
        "loudness": classify_loudness(features, quiet_thresh, loud_thresh),
        "intensity": classify_intensity(features),
    }


# ── CLI ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Tag short UI sound effects with sentiment, duration, loudness, and intensity."
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
