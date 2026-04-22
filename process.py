"""Extract todos from a transcription using Claude and write to Obsidian vault."""

import json
import os
import re
import sys
from datetime import date

import anthropic


def slugify(text: str) -> str:
    """Convert text to a filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def extract_todos(client: anthropic.Anthropic, transcription: str) -> dict:
    """Call Claude to extract todos and suggest titles."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=(
            "You are a professional organizer. For decades you have coached the most happy, "
            "successful, whole, intelligent and abundant people. All people you coach have "
            "transcended and reached higher forms of intelligence, with profound connection "
            "with themself and the world. You are the architect of the universe. You will "
            "receive several ideas and texts that you should help organize them into actions "
            "that will help me to become a better human being and resolve everything.\n\n"
            "Return valid JSON with two keys:\n"
            '- "titles": a list of exactly 3 short, descriptive title suggestions for the todo list\n'
            '- "body": a markdown string with todos as `- [ ]` checklist items, grouped by topic with `##` headings\n'
            "Only include genuinely actionable items. Do not include commentary or preamble in the body."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract all actionable todo items from this transcription and suggest 3 titles.\n\n"
                    f"<transcription>\n{transcription}\n</transcription>"
                ),
            }
        ],
    )

    text = response.content[0].text

    # Try to parse JSON from the response, handling markdown code fences
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        text = json_match.group(1)

    return json.loads(text)


def pick_title(titles: list[str]) -> str:
    """Present title options and let user pick one."""
    print("\nSuggested titles:")
    for i, title in enumerate(titles, 1):
        print(f"  {i}) {title}")
    print(f"  {len(titles) + 1}) Custom (type your own)")

    choice = input(f"\nSelect [1-{len(titles) + 1}]: ").strip()

    try:
        idx = int(choice)
        if 1 <= idx <= len(titles):
            return titles[idx - 1]
    except ValueError:
        pass

    if choice == str(len(titles) + 1) or not choice.isdigit():
        custom = input("Enter custom title: ").strip() if choice.isdigit() else choice
        if custom:
            return custom

    return titles[0]


def main():
    if len(sys.argv) < 2:
        print("Usage: process.py <transcription-file>", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    vault_dir = os.environ.get("OBSIDIAN_VAULT", "/vault")
    input_path = sys.argv[1]

    with open(input_path) as f:
        transcription = f.read().strip()

    if not transcription:
        print("Error: transcription file is empty.", file=sys.stderr)
        sys.exit(1)

    print("Calling Claude to extract todos...")
    client = anthropic.Anthropic(api_key=api_key)
    result = extract_todos(client, transcription)

    titles = result["titles"]
    body = result["body"]

    title = pick_title(titles)
    slug = slugify(title)
    filename = f"{date.today().isoformat()}-{slug}.md"
    output_path = os.path.join(vault_dir, filename)

    with open(output_path, "w") as f:
        f.write(f"# {title}\n\n{body}\n")

    print(f"\nTodos written to: {output_path}")


if __name__ == "__main__":
    main()
