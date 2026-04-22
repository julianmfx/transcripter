#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="transcripter"

usage() {
    echo "Usage: $0 <audio-files...>"
    echo "  Transcribe WhatsApp voice notes (.opus, .ogg, .m4a) to .txt"
    echo ""
    echo "Examples:"
    echo "  $0 ~/Downloads/*.opus"
    echo "  $0 /path/to/notes/audio.ogg"
    exit 1
}

REBUILD=0
args=()
for arg in "$@"; do
    if [ "$arg" = "--rebuild" ]; then
        REBUILD=1
    else
        args+=("$arg")
    fi
done
set -- "${args[@]}"

if [ $# -eq 0 ]; then
    usage
fi

# Build image if not present or --rebuild requested
if [ "$REBUILD" -eq 1 ]; then
    echo "Rebuilding $IMAGE_NAME Docker image..."
    docker build -t "$IMAGE_NAME" "$(dirname "$0")"
elif ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    echo "Building $IMAGE_NAME Docker image (this will take a while on first run)..."
    docker build -t "$IMAGE_NAME" "$(dirname "$0")"
fi

# Collect unique directories and map files to container paths
declare -A dir_map
container_files=()

for file in "$@"; do
    abs_path="$(realpath "$file")"
    if [ ! -f "$abs_path" ]; then
        echo "Warning: file not found: $file" >&2
        continue
    fi
    dir="$(dirname "$abs_path")"
    basename="$(basename "$abs_path")"
    dir_map["$dir"]=1
    container_files+=("/data/${dir//\//_}/$basename")
done

if [ ${#container_files[@]} -eq 0 ]; then
    echo "Error: no valid files provided." >&2
    exit 1
fi

# Build volume mount args and container file paths
volume_args=()
container_files=()

for file in "$@"; do
    abs_path="$(realpath "$file")" 2>/dev/null || continue
    [ -f "$abs_path" ] || continue
    dir="$(dirname "$abs_path")"
    basename="$(basename "$abs_path")"
    # Use a stable mount name derived from the directory
    mount_name="${dir//\//_}"
    volume_args+=("-v" "${dir}:/data/${mount_name}")
    container_files+=("/data/${mount_name}/${basename}")
done

# Deduplicate volume args
declare -A seen_volumes
unique_volume_args=()
for ((i=0; i<${#volume_args[@]}; i+=2)); do
    key="${volume_args[i+1]}"
    if [ -z "${seen_volumes[$key]+x}" ]; then
        seen_volumes["$key"]=1
        unique_volume_args+=("${volume_args[i]}" "${volume_args[i+1]}")
    fi
done

docker run --rm \
    "${unique_volume_args[@]}" \
    "$IMAGE_NAME" \
    "${container_files[@]}"

# After transcription, offer to join all .txt files
# Find the directory of the first input file
first_dir="$(dirname "$(realpath "$1")")"

# Collect .txt files in that directory, sorted by leading number
mapfile -t txt_files < <(find "$first_dir" -maxdepth 1 -name '*.txt' ! -name 'transcription.txt' -printf '%f\n' | sort -n)

output_file="$first_dir/transcription.txt"

if [ ${#txt_files[@]} -gt 1 ]; then
    echo ""
    echo "Found ${#txt_files[@]} transcription files:"
    for f in "${txt_files[@]}"; do
        echo "  $f"
    done
    echo ""
    read -rp "Join all into a single file? [y/N] " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        > "$output_file"
        for f in "${txt_files[@]}"; do
            cat "$first_dir/$f" >> "$output_file"
            echo "" >> "$output_file"
        done
        echo "Joined transcription written to: $output_file"
    fi
fi

# Claude todo extraction
if [ -f "$output_file" ]; then
    echo ""
    read -rp "Extract todos via Claude and save to Obsidian? [y/N] " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
            echo "Error: ANTHROPIC_API_KEY is not set." >&2
            echo "  export ANTHROPIC_API_KEY='sk-ant-...'" >&2
            exit 1
        fi

        # Load .env if present
        if [ -f "$(dirname "$0")/.env" ]; then
            set -a; source "$(dirname "$0")/.env"; set +a
        fi
        if [ ! -d "$OBSIDIAN_VAULT" ]; then
            echo "Error: Obsidian vault not found at $OBSIDIAN_VAULT" >&2
            exit 1
        fi

        docker run --rm -i \
            -v "$first_dir:/data" \
            -v "$OBSIDIAN_VAULT:/vault" \
            -e ANTHROPIC_API_KEY \
            --user "$(id -u):$(id -g)" \
            --entrypoint python \
            "$IMAGE_NAME" \
            /app/process.py /data/transcription.txt
    fi
fi
