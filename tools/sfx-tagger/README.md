# sfx-tagger

A command-line tool that analyses short UI sound effects and tags them across 8 dimensions. Outputs a JSON sidecar file.

Designed for non-speech UI sounds — clicks, chimes, bleeps, whooshes, error buzzes, etc.

## Architecture

```
                    ┌─────────────┐
   WAV files ──────▶│   librosa   │
                    │  (feature   │
                    │ extraction) │
                    └──────┬──────┘
                           │
                    raw feature vector
                    (15 numeric values)
                           │
                    ┌──────▼──────┐
                    │ Rule-based  │
                    │ classifier  │
                    │ (thresholds │
                    │  & scoring) │
                    └──────┬──────┘
                           │
                    8 descriptive tags
                           │
                    ┌──────▼──────┐
                    │  tags.json  │
                    └─────────────┘
```

The tool is a single Python script with two stages: **feature extraction** and **classification**. There are no ML models — every decision is a deterministic rule applied to measured audio properties.

## How it works

### Stage 1: Feature extraction

Each WAV file is loaded with librosa and reduced to a vector of numeric features. These are the raw measurements that all 8 tags are derived from.

| Feature | How it's measured | What it tells us |
|---|---|---|
| **Duration** | `librosa.get_duration` — total length in seconds | How long the sound is |
| **RMS loudness** | `librosa.feature.rms` — root-mean-square energy, converted to dB | Average perceived volume |
| **Crest factor** | Peak amplitude / mean RMS | How "spiky" the waveform is — a sharp click has a high crest factor, a sustained tone has a low one |
| **Attack time** | Frame index of peak RMS × hop length / sample rate | How quickly the sound reaches full volume — a snap is < 5ms, a swell can be hundreds of ms |
| **Decay time** | Time from peak RMS to where RMS drops to 10% of peak (relative threshold, not absolute) | How long the sound rings out after its peak. Uses a relative threshold to handle quiet sounds correctly |
| **Spectral centroid** | `librosa.feature.spectral_centroid` — the "centre of mass" of the frequency spectrum | Brightness. A low rumble might be 200 Hz, a bright ping 5000+ Hz |
| **Spectral rolloff** | `librosa.feature.spectral_rolloff` — frequency below which 85% of energy sits | Another brightness measure, less sensitive to outlier harmonics than centroid |
| **Spectral bandwidth** | `librosa.feature.spectral_bandwidth` — spread of energy around the centroid | Narrow = pure/tonal, wide = complex/noisy |
| **Spectral flatness** | `librosa.feature.spectral_flatness` — ratio of geometric to arithmetic mean of spectrum | 0.0 = perfectly tonal (sine wave), 1.0 = perfectly flat (white noise) |
| **Zero-crossing rate** | `librosa.feature.zero_crossing_rate` — how often the waveform crosses zero per frame | Proxy for noisiness/harshness. A clean sine wave crosses rarely, noise crosses constantly |
| **Centroid slope** | Linear regression over the spectral centroid across active (non-silent) frames only | Whether the sound gets brighter (rising = positive slope) or darker (falling = negative slope) over time. Silent tail frames are excluded to avoid skewing the slope negative |
| **Fundamental frequency** | `librosa.pyin` (fmin=80Hz, fmax=4000Hz) with spectral centroid as fallback | The perceived musical pitch of tonal sounds. Falls back to centroid for noisy/unpitched sounds. Short signals (< 2048 samples) use centroid directly |
| **Harmonic ratio** | Energy of `librosa.effects.harmonic(y)` / total energy | How much of the sound is clean harmonic content vs noise (HPSS-based) |
| **Peak autocorrelation** | `librosa.autocorrelate` — normalised peak of the autocorrelation function after lag 0 | How periodic/repetitive the signal is. Catches tonal synthesised sounds that HPSS misclassifies. A pure tone approaches 1.0, noise approaches 0.0 |
| **Onset count** | `librosa.onset.onset_detect` — number of detected note/event onsets | Whether the sound is a single event or a sequence |
| **RMS envelope shape** | RMS energy over time, analysed for attack/sustain/decay proportions | The temporal "shape" of the sound |

### Stage 2: Classification

Each tag is computed independently by applying rules to the feature vector. No tag depends on any other tag's output.

---

#### Sentiment: `positive` | `negative` | `neutral`

**What it captures:** Whether the sound feels affirming, alarming, or neutral — the emotional valence of the sound.

**How it's measured:** A scoring system based on three features:

- **Spectral centroid** (brightness): Bright sounds (centroid > 3000 Hz) score positive. Dark sounds (< 1500 Hz) score negative. This is the strongest signal — decades of sound design convention associates bright tones with success and dark tones with errors.
- **Spectral rolloff** (energy distribution): High rolloff (> 6000 Hz) adds a positive half-point. Low rolloff (< 3000 Hz) adds a negative half-point. This catches sounds where the centroid is mid-range but the overall energy skews bright or dark.
- **Centroid slope** (pitch direction): Rising pitch (slope > 5) scores positive — think of an ascending chime confirming an action. Falling pitch (slope < -5) scores negative — think of a descending buzz indicating failure.

The scores are summed. Total >= 1 = positive, <= -1 = negative, otherwise neutral.

---

#### Duration: `short` | `medium` | `long`

**What it captures:** Perceived length of the sound.

**How it's measured:** Direct comparison of `librosa.get_duration` against two configurable thresholds:
- Short: < 0.25 seconds (a click, a tap)
- Long: > 0.8 seconds (a notification, a transition)
- Medium: everything between

These defaults are tuned for UI sound effects. A game SFX library might need different thresholds.

---

#### Loudness: `quiet` | `medium` | `loud`

**What it captures:** Average perceived volume relative to full-scale.

**How it's measured:** Mean RMS energy is converted to dB (`20 × log10(mean_rms)`). This gives a value roughly analogous to LUFS for short samples. Compared against two configurable thresholds:
- Quiet: < -28 dB
- Loud: > -16 dB
- Medium: between

Note: these are relative to digital full-scale (0 dBFS), not absolute SPL. A "quiet" sound is quiet relative to the maximum possible level in the file.

---

#### Intensity: `soft` | `medium` | `intense`

**What it captures:** How aggressive or punchy the sound feels — distinct from loudness. A sound can be quiet but intense (a sharp, thin click) or loud but soft (a warm pad swell).

**How it's measured:** A composite score from three features, each contributing +1 or -1:

- **Crest factor** (> 8 = intense, < 4 = soft): High crest factor means sharp transients relative to the average level — the sound "pokes out" of the waveform.
- **Attack time** (< 20ms = intense, > 100ms = soft): Fast attacks feel snappy and aggressive. Slow attacks feel gentle.
- **Zero-crossing rate** (> 0.15 = intense, < 0.05 = soft): High ZCR means the waveform is jagged and buzzy. Low ZCR means it's smooth.

Score >= 1.5 = intense, <= -1.5 = soft, otherwise medium.

---

#### Pitch: `low` | `mid` | `high`

**What it captures:** The perceived pitch register of the sound.

**How it's measured:** For tonal sounds, `librosa.pyin` estimates the fundamental frequency — the actual musical pitch. For noisy sounds where pitch tracking fails, the spectral centroid is used as a fallback (it correlates well with perceived pitch for broadband sounds).

The frequency is mapped to perceptual bands:
- Low: < 300 Hz — thuds, rumbles, bass tones
- Mid: 300–2000 Hz — most UI bleeps, notification tones
- High: > 2000 Hz — bright pings, clicks, sparkles

These bands roughly correspond to how the human ear groups sounds by register. The 300 Hz boundary sits just above typical "bass" content, and 2000 Hz is where sounds start to feel distinctly "bright" or "treble".

---

#### Envelope: `percussive` | `sustained` | `swelling` | `decaying`

**What it captures:** The temporal shape of the sound — how its energy evolves over time.

**How it's measured:** The RMS energy curve is analysed in three phases:

1. **Attack phase**: from onset to peak RMS. Measured as a proportion of total duration.
2. **Sustain phase**: the portion where RMS stays within a threshold of the peak (e.g. within 6 dB).
3. **Decay phase**: from end of sustain to silence (or end of file).

Classification rules:
- **Percussive**: attack < 20ms AND decay < 60% of duration — the energy appears and disappears quickly (clicks, taps, hits)
- **Swelling**: attack > 50% of duration — the sound spends most of its time getting louder (power-ups, build-ups, risers)
- **Decaying**: attack < 20% of duration AND decay > 60% of duration — quick onset followed by a long ring-out (chimes, bells, pings, reverb tails)
- **Sustained**: everything else — relatively flat energy throughout (drones, held tones, loops)

---

#### Tonality: `tonal` | `noisy`

**What it captures:** Whether the sound has a clear pitch or is more like filtered noise/texture.

**How it's measured:** Two complementary features are combined:

- **Autocorrelation periodicity**: The signal is autocorrelated and the strongest peak after lag 0 is measured. A periodic signal (tonal) produces a strong peak approaching 1.0; aperiodic noise stays near 0.0. This is the primary tonality signal because it reliably detects synthesised tones that HPSS-based harmonic separation misclassifies.
- **Spectral flatness**: Measures how "flat" the frequency spectrum is. A perfectly flat spectrum (all frequencies equally loud = noise) gives 1.0. A spectrum with sharp peaks (= tonal content) gives close to 0.0.
- **Harmonic ratio** (HPSS): The audio is decomposed into harmonic and percussive components using `librosa.effects.harmonic`. Used as a secondary signal when autocorrelation and flatness are ambiguous.

These three measures are complementary — autocorrelation works in the time domain, spectral flatness in the frequency domain, and HPSS uses a spectrogram decomposition. The sound is classified as **tonal** if autocorrelation is strong (> 0.5), or spectral flatness is low (< 0.15), or autocorrelation and flatness both suggest tonality. It is **noisy** if spectral flatness is high (> 0.5) or none of the tonal conditions are met.

---

#### Type: `click` | `beep` | `chime` | `whoosh` | `buzz` | `thud` | `sweep`

**What it captures:** A perceptual category label — what a human would call this kind of sound.

**How it's measured:** This is the most heuristic-heavy classifier. It uses combinations of features from the other dimensions rather than its own dedicated measurement. Rules are evaluated in priority order (first match wins):

| Type | Rule |
|---|---|
| **Click** | Duration < 50ms, percussive envelope, high spectral flatness (broadband) |
| **Thud** | Percussive envelope, low pitch (< 300 Hz), dark (low centroid) |
| **Buzz** | Noisy tonality, sustained envelope, high ZCR, mid-low pitch |
| **Whoosh** | Noisy tonality, strong centroid slope (rising or falling), medium-long duration |
| **Sweep** | Strong centroid slope, tonal or noisy, medium-long duration |
| **Chime** | Tonal, high pitch, decaying envelope |
| **Beep** | Tonal, short-medium duration (fallback for tonal sounds that don't match chime) |

The ordering matters — a very short broadband transient is a click before it could be a thud, and a tonal decaying sound is a chime before it could be a beep. This priority chain handles the overlapping feature spaces between types.

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
    "intensity": "soft",
    "pitch": "high",
    "envelope": "percussive",
    "tonality": "tonal",
    "type": "click"
  },
  "error_buzz.wav": {
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

With `--verbose`, each entry also includes the raw feature values used for classification:

```json
{
  "click_ok.wav": {
    "tags": {
      "sentiment": "positive",
      "duration": "short",
      "loudness": "quiet",
      "intensity": "soft",
      "pitch": "high",
      "envelope": "percussive",
      "tonality": "tonal",
      "type": "click"
    },
    "features": {
      "duration": 0.13,
      "rms_db": -31.5,
      "crest_factor": 14.0,
      "attack_time": 0.01,
      "decay_time": 0.08,
      "spectral_centroid": 4200.0,
      "spectral_rolloff": 7500.0,
      "spectral_bandwidth": 2100.0,
      "spectral_flatness": 0.02,
      "zcr": 0.18,
      "centroid_slope": 120.5,
      "fundamental_freq": 4400.0,
      "harmonic_ratio": 0.85,
      "peak_autocorr": 0.92,
      "onset_count": 1
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

## Reviewing results

The interactive review tool lets you listen to each sound, see its tags, and correct any misclassifications:

```bash
# Review all sounds in a pack
python3 tools/sfx-tagger/review.py path/to/tags.json

# Review only sounds with a specific tag
python3 tools/sfx-tagger/review.py path/to/tags.json --filter sentiment=neutral
python3 tools/sfx-tagger/review.py path/to/tags.json --filter type=buzz
```

For each sound, the tool displays the current tags (with all options shown), plays the audio, and waits for input:

- **Enter** or **`a`** — accept the tags as-is
- **`r`** — replay the sound
- **`s`** — skip (leave unchanged)
- **`<field> <value>`** — change a tag (e.g. `sentiment positive`, or abbreviated: `sen pos`)
- **Ctrl+C** — quit and save any changes made so far

Corrections are written back to the same `tags.json` file.

## Limitations

- WAV files only (MP3 and other formats are not supported)
- Sentiment classification is tuned for non-speech UI sounds — results on voice clips or music will not be meaningful
- Sound type classification is heuristic and priority-ordered — edge cases between categories (e.g. a very short chime vs a beep) may not always match human intuition
- Thresholds are hand-tuned defaults; different sound libraries may need adjustment
