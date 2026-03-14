# Plan: `sfx-tagger` — CLI tool for categorising UI sound effects

## Goal

A Python CLI that analyses short audio UI sound effect files and outputs a JSON sidecar with descriptive tags across 8 dimensions: sentiment, duration, loudness, intensity, pitch register, envelope shape, tonality, and sound type.

## Scope

- **Non-speech UI sound effects only** (bleeps, clicks, chimes, whooshes, error buzzes, etc.)
- Standalone JSON output (`tags.json`)
- No ML models or large dependencies — librosa + sox/ffmpeg only

## Architecture

Single Python CLI script with two stages:

```
WAV files → [Feature Extraction] → [Rule-Based Classifier] → tags.json
```

### Feature extraction (librosa)

For each file, compute:

| Feature | Library call | Used for |
|---|---|---|
| Duration (seconds) | `librosa.get_duration` | short / long |
| RMS loudness | `librosa.feature.rms` | quiet / loud |
| Crest factor (peak / RMS) | `np.max(np.abs(y)) / mean_rms` | soft / intense |
| Attack time | Time from onset to peak RMS | soft / intense |
| Spectral centroid | `librosa.feature.spectral_centroid` | positive / negative |
| Spectral rolloff | `librosa.feature.spectral_rolloff` | positive / negative |
| Zero-crossing rate | `librosa.feature.zero_crossing_rate` | soft / intense |
| Pitch direction | Centroid slope over time (linear regression) | positive / negative |
| Fundamental frequency | `librosa.yin` or `librosa.pyin` | pitch register |
| Harmonic-to-noise ratio | Harmonic energy / total energy via `librosa.effects.harmonic` | tonality |
| Spectral flatness | `librosa.feature.spectral_flatness` | tonality |
| RMS envelope shape | RMS over time: attack/sustain/release curve analysis | envelope |
| Onset count | `librosa.onset.onset_detect` | sound type |
| Spectral bandwidth | `librosa.feature.spectral_bandwidth` | sound type |
| Decay time | Time from peak RMS to silence (e.g. -40dB) | envelope, sound type |

### Rule-based classification

**Sentiment (positive / negative / neutral):**
- **Positive**: high spectral centroid (bright), rising pitch direction, moderate-high loudness
- **Negative**: low spectral centroid (dark), falling or flat pitch, abrupt/harsh transients
- **Neutral**: mid-range centroid, short duration, low intensity, minimal pitch movement

This replaces speech-to-text/sentiment — for non-speech UI sounds, spectral brightness and pitch contour are reliable proxies for perceived valence. Research backs this up: rising bright tones feel affirming, falling dark tones feel like errors.

**Duration:** configurable thresholds (defaults: short < 0.25s, long > 0.8s)

**Loudness:** configurable thresholds via integrated RMS (defaults: quiet < -28 LUFS-equivalent, loud > -16)

**Intensity:** composite of crest factor, attack time, and zero-crossing rate

**Pitch register (low / mid / high):**
Based on the dominant fundamental frequency or spectral centroid mapped to perceptual bands:
- **Low**: < 300 Hz — thuds, rumbles, bass tones
- **Mid**: 300–2000 Hz — most UI bleeps and chimes
- **High**: > 2000 Hz — bright pings, clicks, sparkles

**Envelope shape (percussive / sustained / swelling / decaying):**
Derived from the RMS energy curve over time:
- **Percussive**: fast attack (< 20ms), short sustain, fast decay — clicks, taps, hits
- **Sustained**: relatively flat RMS throughout the sound's duration
- **Swelling**: RMS rises over time (attack time > 50% of duration) — power-ups, build-ups
- **Decaying**: fast attack followed by a long tail (decay > 60% of duration) — chimes, bells, pings

**Tonality (tonal / noisy):**
Composite of harmonic-to-noise ratio and spectral flatness:
- **Tonal**: strong harmonic content, low spectral flatness — clean beeps, chimes, melodic tones
- **Noisy**: weak harmonics, high spectral flatness — static, whooshes, buzzes, texture

**Sound type (click / beep / chime / whoosh / buzz / thud / sweep):**
Heuristic classification combining multiple features:
- **Click**: very short (< 50ms), percussive, broadband (high spectral flatness)
- **Beep**: short, tonal, mid-high pitch, percussive or sustained
- **Chime**: tonal, high pitch, decaying envelope, resonant
- **Whoosh**: noisy, sustained or swelling, rising or falling centroid slope
- **Buzz**: noisy, sustained, harsh (high ZCR), mid-low pitch
- **Thud**: percussive, low pitch, dark (low centroid), short decay
- **Sweep**: tonal or noisy, strong centroid slope (rising or falling), medium-long duration

## CLI interface

```bash
python3 tools/sfx-tagger/sfx_tagger.py ./sounds/*.wav \
  --out tags.json \
  --short-threshold 0.25 \
  --long-threshold 0.8 \
  --loud-threshold -16 \
  --quiet-threshold -28
```

### Output format

```json
{
  "click_ok_01.wav": {
    "sentiment": "positive",
    "duration": "short",
    "loudness": "quiet",
    "intensity": "soft",
    "pitch": "high",
    "envelope": "percussive",
    "tonality": "tonal",
    "type": "click"
  },
  "error_buzz_02.wav": {
    "sentiment": "negative",
    "duration": "short",
    "loudness": "loud",
    "intensity": "intense",
    "pitch": "mid",
    "envelope": "sustained",
    "tonality": "noisy",
    "type": "buzz"
  }
}
```

Each file gets exactly 8 tags:
1. Sentiment: `positive` | `negative` | `neutral`
2. Duration: `short` | `medium` | `long`
3. Loudness: `quiet` | `medium` | `loud`
4. Intensity: `soft` | `medium` | `intense`
5. Pitch: `low` | `mid` | `high`
6. Envelope: `percussive` | `sustained` | `swelling` | `decaying`
7. Tonality: `tonal` | `noisy`
8. Type: `click` | `beep` | `chime` | `whoosh` | `buzz` | `thud` | `sweep`

## File structure

```
tools/sfx-tagger/
  sfx_tagger.py        # CLI entry point + all logic
  requirements.txt     # librosa, numpy, soundfile
```

## Dependencies

- Python 3.9+
- `librosa` (pulls in numpy, soundfile, etc.)
- No other external dependencies — sox/ffmpeg only needed if librosa can't read a format directly

## Steps

1. Create `tools/sfx-tagger/` directory
2. Write `requirements.txt`
3. Implement feature extraction functions
4. Implement rule-based classifier with configurable thresholds
5. Wire up argparse CLI
6. Test against a handful of known UI SFX files to sanity-check tags
7. Document usage in script docstring

## Out of scope (for MVP)

- Training a classifier / ML models
- Writing tags into audio file metadata
- CESP category mapping
- Batch re-tagging or watch mode
- Support for non-WAV formats
