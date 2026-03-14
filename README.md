# PeonPing

Tools and sound packs for [OpenPeon](https://github.com/PeonPing/openpeon) — audio feedback for coding tools.

## What's in this repo

- **`openpeon-classic/`** — A Worms-style voice pack (ready to use)
- **`tools/sfx-tagger/`** — CLI tool for analysing and tagging UI sound effects
- **`samples/`** — Source audio samples (gitignored)

## Creating a Sound Pack

An OpenPeon sound pack is a directory containing an `openpeon.json` manifest and a `sounds/` folder. Packs follow the [CESP v1.0 spec](https://github.com/PeonPing/openpeon/blob/main/spec/cesp-v1.md).

### Directory structure

```
my-pack/
  openpeon.json       # manifest (required)
  sounds/             # audio files (required)
    Hello.mp3
    Error.wav
    ...
  icons/              # icon files (optional)
    pack.png
  README.md           # pack description (optional)
  LICENSE             # license file (optional)
```

### The manifest

`openpeon.json` maps your sounds to CESP event categories. Here's a minimal example:

```json
{
  "cesp_version": "1.0",
  "name": "my-pack",
  "display_name": "My Sound Pack",
  "version": "1.0.0",
  "categories": {
    "task.complete": {
      "sounds": [
        { "file": "sounds/success.wav", "label": "Success!" },
        { "file": "sounds/nice-work.wav", "label": "Nice work" }
      ]
    },
    "task.error": {
      "sounds": [
        { "file": "sounds/oops.wav", "label": "Oops" }
      ]
    }
  }
}
```

Add recommended fields for registry submission:

```json
{
  "cesp_version": "1.0",
  "name": "my-pack",
  "display_name": "My Sound Pack",
  "version": "1.0.0",
  "description": "Short description of your pack",
  "author": { "name": "Your Name", "github": "your-github" },
  "license": "CC-BY-4.0",
  "language": "en",
  "homepage": "https://github.com/you/openpeon-my-pack",
  "tags": ["comedy", "gaming"],
  "categories": { ... }
}
```

### Event categories

Your pack maps sounds to these categories. Players pick a random sound from each category when the event fires.

#### Core categories (at least one required)

| Category | When it fires | Example sounds |
|---|---|---|
| `session.start` | IDE opens, agent connects | "Hello", "Ready to work" |
| `task.acknowledge` | Command accepted, build starting | "On it", "Working..." |
| `task.complete` | Build done, test passed, task finished | "Done!", "Excellent" |
| `task.error` | Build failure, crash, test failure | "Oops", "That's broken" |
| `input.required` | Waiting for user approval or input | "Your turn", "Waiting..." |
| `resource.limit` | Rate limit, token limit, quota hit | "Slow down", "Out of juice" |

#### Extended categories (optional)

| Category | When it fires |
|---|---|
| `user.spam` | User sending commands too rapidly |
| `session.end` | Session closes gracefully |
| `task.progress` | Long-running task still going |

### Sound entry fields

Each sound in a category has these fields:

| Field | Required | Description |
|---|---|---|
| `file` | Yes | Path to audio file, relative to manifest. Use forward slashes. |
| `label` | Yes | Human-readable description (for accessibility and display). |
| `sha256` | For registry | SHA-256 hex digest of the file. |
| `icon` | No | Path to an icon image for this sound. |

### Audio file rules

- **Formats**: WAV, MP3, or OGG Vorbis
- **Max file size**: 1 MB per file
- **Max pack size**: 50 MB total
- **Filenames**: alphanumeric, dots, underscores, hyphens only — no spaces, no Unicode
- Files must be valid audio (checked via magic bytes)

### Icons (optional)

- **Format**: PNG (required support), JPEG, WebP, SVG (optional support)
- **Max size**: 500 KB per icon
- **Recommended dimensions**: 256x256 px
- Players resolve icons in order: sound-level > category-level > pack-level > `icon.png` at root

### Backward compatibility

If migrating from an older peon-ping `manifest.json`, add a `category_aliases` field to support legacy category names:

```json
{
  "category_aliases": {
    "greeting": "session.start",
    "acknowledge": "task.acknowledge",
    "complete": "task.complete",
    "error": "task.error",
    "permission": "input.required",
    "resource_limit": "resource.limit",
    "annoyed": "user.spam"
  }
}
```

### Publishing to the registry

1. Add `sha256` checksums to every sound entry
2. Include `author.github` and `license` fields
3. Tag a release: `git tag v1.0.0 && git push origin v1.0.0`
4. Submit a PR to the [registry](https://github.com/PeonPing/registry)

You can also use the [guided pack creator](https://openpeon.com/create).

### Quick checklist

- [ ] `openpeon.json` at the root with `cesp_version: "1.0"`
- [ ] `name` matches `^[a-z0-9][a-z0-9_-]*$` (1-64 chars)
- [ ] `version` follows semver (e.g. `1.0.0`)
- [ ] At least one core category has sounds
- [ ] All `file` paths resolve to existing audio files
- [ ] Audio files are WAV, MP3, or OGG and under 1 MB each
- [ ] Total pack size under 50 MB
- [ ] No spaces or Unicode in filenames
- [ ] `label` provided for every sound entry

## Using sfx-tagger

See [tools/sfx-tagger/README.md](tools/sfx-tagger/README.md) for the audio analysis tool that can help you tag and categorise sound effects.
