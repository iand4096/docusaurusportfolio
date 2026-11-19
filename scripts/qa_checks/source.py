"""Source text and path matching shared by check adapters."""
from pathlib import Path


def find_source_line(content, original, preferred_line=None):
    """Return the source line on which an exact quoted fragment starts."""

    positions = []
    start = 0

    while True:
        index = content.find(original, start)

        if index == -1:
            break

        positions.append(content.count("\n", 0, index) + 1)
        start = index + 1

    if not positions:
        return None
    if isinstance(preferred_line, int) and preferred_line > 0:
        return min(positions, key=lambda line: abs(line - preferred_line))

    return positions[0]


def source_line_text(content, line_number):
    lines = content.splitlines()

    if 1 <= line_number <= len(lines):
        return lines[line_number - 1]

    return ""

def match_source_path(raw_path, paths):
    """Match a tool output path to an input document."""

    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    candidate = raw_path.strip().replace("\\", "/")
    while candidate.startswith("./"):
        candidate = candidate[2:]

    aliases = {}

    for path in paths:
        relative = path.as_posix()
        aliases[relative] = path

        try:
            aliases[path.resolve().as_posix()] = path
        except OSError:
            pass

    if candidate in aliases:
        return aliases[candidate]
    try:
        resolved = Path(raw_path).resolve().as_posix()
    except OSError:
        return None

    return aliases.get(resolved)
