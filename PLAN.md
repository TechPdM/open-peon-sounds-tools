# Plan: `sfx-tagger` — CLI tool for categorising UI sound effects

## Goal

A Python CLI that analyses short audio UI sound effect files and outputs a JSON sidecar with descriptive tags: positive/negative/neutral, short/long, loud/quiet, soft/intense.

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

### Rule-based classification

**Sentiment (positive / negative / neutral):**
- **Positive**: high spectral centroid (bright), rising pitch direction, moderate-high loudness
- **Negative**: low spectral centroid (dark), falling or flat pitch, abrupt/harsh transients
- **Neutral**: mid-range centroid, short duration, low intensity, minimal pitch movement

This replaces speech-to-text/sentiment — for non-speech UI sounds, spectral brightness and pitch contour are reliable proxies for perceived valence. Research backs this up: rising bright tones feel affirming, falling dark tones feel like errors.

**Duration:** configurable thresholds (defaults: short < 0.25s, long > 0.8s)

**Loudness:** configurable thresholds via integrated RMS (defaults: quiet < -28 LUFS-equivalent, loud > -16)

**Intensity:** composite of crest factor, attack time, and zero-crossing rate

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
  "click_ok_01.wav": ["positive", "short", "quiet", "soft"],
  "error_buzz_02.wav": ["negative", "short", "loud", "intense"],
  "panel_open_01.wav": ["neutral", "long", "medium", "soft"]
}
```

Each file gets exactly 4 tags:
1. Sentiment: `positive` | `negative` | `neutral`
2. Duration: `short` | `medium` | `long`
3. Loudness: `quiet` | `medium` | `loud`
4. Intensity: `soft` | `medium` | `intense`

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
