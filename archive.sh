#!/usr/bin/env bash
set -euo pipefail

# Usage: archive.sh <title> <notes-dir> <files...>
title="$1"
notes_dir="$2"
shift 2

dest="$notes_dir/$title"
mkdir -p "$dest"

moved=0
for file in "$@"; do
    if [ -f "$file" ]; then
        mv "$file" "$dest/"
        ((moved++)) || true
    fi
done

echo "Archived $moved file(s) to: $dest"
