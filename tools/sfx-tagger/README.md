# sfx-tagger

A command-line tool that analyses short UI sound effects and tags them by sentiment, duration, loudness, and intensity. Outputs a JSON sidecar file.

Designed for non-speech UI sounds — clicks, chimes, bleeps, whooshes, error buzzes, etc.

## How it works

Each WAV file is analysed using librosa to extract audio features:

| Feature | What it measures |
|---|---|
| Spectral centroid | Brightness — higher = brighter/more positive |
| Spectral rolloff | Energy distribution — higher = brighter |
| Centroid slope | Pitch direction over time — rising = positive, falling = negative |
| RMS loudness | Average volume in dB |
| Crest factor | Peak-to-average ratio — higher = sharper transient |
| Attack time | Time to peak loudness — faster = more intense |
| Zero-crossing rate | Signal harshness — higher = buzzier/more intense |

These features are fed into a rule-based classifier that produces four tags per file:

| Tag | Values |
|---|---|
| Sentiment | `positive`, `negative`, `neutral` |
| Duration | `short`, `medium`, `long` |
| Loudness | `quiet`, `medium`, `loud` |
| Intensity | `soft`, `medium`, `intense` |

## Installation

```bash
pip install -r tools/sfx-tagger/requirements.txt
```

Requires Python 3.9+.

## Usage

```bash
# Tag all WAVs in a directory (writes tags.json alongside the samples)
python3 tools/sfx-tagger/sfx_tagger.py ./sounds/*.wav

# Write output to a specific file instead
python3 tools/sfx-tagger/sfx_tagger.py ./sounds/*.wav --out /path/to/tags.json

# Include raw feature values alongside tags
python3 tools/sfx-tagger/sfx_tagger.py ./sounds/*.wav --verbose

# Custom thresholds
python3 tools/sfx-tagger/sfx_tagger.py ./sounds/*.wav \
  --short-threshold 0.2 \
  --long-threshold 1.0 \
  --loud-threshold -14 \
  --quiet-threshold -30
```

## Output format

```json
{
  "click_ok.wav": {
    "sentiment": "positive",
    "duration": "short",
    "loudness": "quiet",
    "intensity": "soft"
  },
  "error_buzz.wav": {
    "sentiment": "negative",
    "duration": "short",
    "loudness": "loud",
    "intensity": "intense"
  }
}
```

With `--verbose`, each entry also includes the raw feature values used for classification:

```json
{
  "click_ok.wav": {
    "tags": {
      "sentiment": "positive",
      "duration": "short",
      "loudness": "quiet",
      "intensity": "soft"
    },
    "features": {
      "duration": 0.13,
      "rms_db": -31.5,
      "crest_factor": 14.0,
      "attack_time": 0.01,
      "spectral_centroid": 4200.0,
      "spectral_rolloff": 7500.0,
      "zcr": 0.18,
      "centroid_slope": 120.5
    }
  }
}
```

## Options

| Flag | Default | Description |
|---|---|---|
| `--out`, `-o` | `tags.json` in input directory | Output JSON file path |
| `--short-threshold` | `0.25` | Duration in seconds below which a sound is tagged "short" |
| `--long-threshold` | `0.8` | Duration in seconds above which a sound is tagged "long" |
| `--loud-threshold` | `-16` | RMS dB above which a sound is tagged "loud" |
| `--quiet-threshold` | `-28` | RMS dB below which a sound is tagged "quiet" |
| `--verbose`, `-v` | off | Include raw feature values in output |

## Limitations

- WAV files only (MP3 and other formats are not supported)
- Sentiment classification is tuned for non-speech UI sounds — results on voice clips or music will not be meaningful
- Thresholds are hand-tuned defaults; different sound libraries may need adjustment
