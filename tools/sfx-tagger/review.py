#!/usr/bin/env python3
"""Interactive review tool for sfx-tagger output.

Plays each sound, shows current tags, and lets you accept or correct them.
Writes corrected tags back to tags.json.

Usage:
    python3 review.py path/to/tags.json
    python3 review.py path/to/tags.json --filter type=buzz    # only review buzzes
    python3 review.py path/to/tags.json --filter sentiment=neutral  # only review neutrals
"""

import argparse
import json
import os
import subprocess
import sys


TAG_OPTIONS = {
    "sentiment": ["positive", "negative", "neutral"],
    "duration": ["short", "medium", "long"],
    "loudness": ["quiet", "medium", "loud"],
    "intensity": ["soft", "medium", "intense"],
    "pitch": ["low", "mid", "high"],
    "envelope": ["percussive", "sustained", "swelling", "decaying"],
    "tonality": ["tonal", "noisy"],
    "type": ["click", "beep", "chime", "whoosh", "buzz", "thud", "sweep"],
}


def play(filepath):
    """Play a WAV file using the system player."""
    try:
        subprocess.run(["afplay", filepath], check=True, timeout=30)
    except FileNotFoundError:
        # Fallback for non-macOS
        subprocess.run(["aplay", filepath], check=True, timeout=30)


def print_tags(tags):
    """Print current tags in a readable format."""
    for key, value in tags.items():
        options = TAG_OPTIONS.get(key, [])
        opts_str = "  ".join(
            f"[{o}]" if o == value else f" {o} "
            for o in options
        )
        print(f"  {key:12s}: {opts_str}")


def prompt_correction(tags):
    """Prompt user to correct tags. Returns updated tags dict."""
    updated = dict(tags)
    print()
    print("  Commands: (r)eplay  (a)ccept  (s)kip  or type <field> <value> to change")
    print()

    while True:
        try:
            inp = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return None  # signal to quit

        if not inp or inp == "a":
            return updated

        if inp == "s":
            return tags  # return original, no changes

        if inp == "r":
            return "replay"

        parts = inp.split(None, 1)
        if len(parts) == 2:
            field, value = parts

            # Allow abbreviated field names
            matches = [k for k in TAG_OPTIONS if k.startswith(field)]
            if len(matches) == 1:
                field = matches[0]
            elif len(matches) == 0:
                print(f"    unknown field: {field}")
                continue

            # Allow abbreviated values
            valid = TAG_OPTIONS.get(field, [])
            val_matches = [v for v in valid if v.startswith(value)]
            if len(val_matches) == 1:
                value = val_matches[0]
            elif value not in valid:
                print(f"    invalid value for {field}: {value}")
                print(f"    options: {', '.join(valid)}")
                continue

            updated[field] = value
            print()
            print_tags(updated)
            print()
            print("  (a)ccept  or make more changes")
        else:
            print("    usage: <field> <value>, (r)eplay, (a)ccept, or (s)kip")


def main():
    parser = argparse.ArgumentParser(description="Interactively review sfx-tagger output")
    parser.add_argument("tags_file", help="Path to tags.json")
    parser.add_argument("--filter", help="Only review entries matching field=value (e.g. sentiment=neutral)")
    args = parser.parse_args()

    tags_path = args.tags_file
    sounds_dir = os.path.dirname(os.path.abspath(tags_path))

    with open(tags_path) as f:
        data = json.load(f)

    # Apply filter
    entries = list(data.items())
    if args.filter:
        field, value = args.filter.split("=", 1)
        entries = [(name, tags) for name, tags in entries if tags.get(field) == value]

    if not entries:
        print("No entries to review.")
        return

    changes = 0
    total = len(entries)

    print(f"\nReviewing {total} sounds from {tags_path}\n")
    print("─" * 60)

    i = 0
    while i < total:
        name, tags = entries[i]
        wav_path = os.path.join(sounds_dir, name)

        print(f"\n[{i+1}/{total}] {name}")
        print()
        print_tags(tags)

        if os.path.isfile(wav_path):
            play(wav_path)
        else:
            print(f"  (file not found: {wav_path})")

        result = prompt_correction(tags)

        if result is None:
            # Quit
            break
        elif result == "replay":
            continue  # replay same file
        elif result != tags:
            data[name] = result
            changes += 1
            print("    ✓ updated")

        i += 1

    if changes > 0:
        with open(tags_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(f"\nSaved {changes} changes to {tags_path}")
    else:
        print("\nNo changes made.")


if __name__ == "__main__":
    main()
