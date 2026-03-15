# PeonPing

Sound packs and tools for [PeonPing](https://github.com/PeonPing/peon-ping) — audio feedback notifications for coding tools like Claude Code.

PeonPing plays short sound effects when coding events happen: a task completes, an error occurs, input is needed, or a session starts. Sound packs define which sounds play for each event.

## Sound packs

Packs in this repo follow the [OpenPeon](https://github.com/PeonPing/openpeon) format and the [CESP v1.0 spec](https://github.com/PeonPing/openpeon/blob/main/spec/cesp-v1.md).

| Pack | Style | Sounds | Categories | License |
|---|---|---|---|---|
| [cute-minimal](openpeon-cute-minimal/) | Light, playful UI beeps | 7 | 7 | MIT |
| [dreamy-minimal](openpeon-dreamy-minimal/) | Soft, warm tonal beeps | 7 | 7 | MIT |
| [nightflame-minimal](openpeon-nightflame-minimal/) | Minimal sweeps and tones | 7 | 7 | MIT |
| [modern-varied](openpeon-modern-varied/) | Cyberpunk synth UI effects | 28 | 7 | MIT |
| [nezuai-varied](openpeon-nezuai-varied/) | Designed whooshes, beeps, thuds | 17 | 7 | MIT |

### Installing a pack

Symlink the pack directory into `~/.openpeon/packs/`:

```bash
ln -s /path/to/openpeon-cute-minimal ~/.openpeon/packs/cute-minimal
```

Then set it as the active pack in your PeonPing config, or use `/peon-ping-use cute-minimal` in Claude Code.

## CESP v1.0 overview

The [Coding Event Sound Pack](https://github.com/PeonPing/openpeon/blob/main/spec/cesp-v1.md) specification defines how sound packs are structured. Key requirements:

### Manifest (`openpeon.json`)

Every pack has an `openpeon.json` at its root with:

- `cesp_version` — must be `"1.0"`
- `name` — lowercase alphanumeric with hyphens/underscores, 1-64 chars
- `display_name` — human-readable name
- `version` — semver (e.g. `1.0.0`)
- `categories` — maps event categories to arrays of sound entries
- `author`, `license`, `description`, `tags` — recommended for registry submission
- `sha256` on each sound entry — required for registry submission

### Event categories

Packs map sounds to these categories. The player picks a random sound from the category when the event fires.

| Category | When it fires |
|---|---|
| `session.start` | IDE opens, agent connects |
| `task.acknowledge` | Command accepted, build starting |
| `task.complete` | Build done, test passed, task finished |
| `task.error` | Build failure, crash, test failure |
| `input.required` | Waiting for user approval or input |
| `resource.limit` | Rate limit, token limit, quota hit |
| `user.spam` | User sending commands too rapidly |

At least one core category (`session.start` through `resource.limit`) must have sounds.

### Audio constraints

- **Formats**: WAV, MP3, or OGG Vorbis
- **Max file size**: 1 MB per file
- **Max pack size**: 50 MB total
- **Filenames**: alphanumeric, dots, underscores, hyphens only — no spaces or Unicode
- **Recommended**: 44.1 kHz, 16-bit

### Pack structure

```
my-pack/
  openpeon.json       # manifest (required)
  sounds/             # audio files (required)
  icons/              # icon files (optional, PNG/JPEG/WebP/SVG, max 500KB)
  README.md           # description (optional)
  LICENSE             # license (optional)
```

See the [full CESP v1.0 spec](https://github.com/PeonPing/openpeon/blob/main/spec/cesp-v1.md) for complete details.

## Tools

### sfx-tagger

A CLI tool that analyses short UI sound effects and classifies them across 8 dimensions: sentiment, duration, loudness, intensity, pitch, envelope, tonality, and type.

Useful for mapping unfamiliar sound libraries to CESP categories — run sfx-tagger to understand what each sound "feels like", then assign them to the right events.

```bash
# Install dependencies
pip install -r tools/sfx-tagger/requirements.txt

# Tag all WAVs in a directory
python3 tools/sfx-tagger/sfx_tagger.py ./sounds/*.wav

# Include raw feature values
python3 tools/sfx-tagger/sfx_tagger.py ./sounds/*.wav --verbose
```

Includes an interactive review tool for verifying and correcting tags:

```bash
python3 tools/sfx-tagger/review.py path/to/tags.json
```

See [tools/sfx-tagger/README.md](tools/sfx-tagger/README.md) for full documentation of the analysis architecture, all 15 extracted features, and the 8 classifiers.
