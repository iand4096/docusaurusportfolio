"""Read-only ingestion from governed Docusaurus docs. No taxonomy mutations."""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote
import yaml


def validate_source(repo: Path) -> None:
    cmd = ['python', 'scripts/taxonomy.py', 'check', '--all']
    result = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError('Governance check failed; index not updated.\n' + (result.stdout + result.stderr)[-4500:])


def split_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, flags=re.S)
    if not m:
        return {}, text
    metadata = yaml.safe_load(m.group(1)) or {}
    if not isinstance(metadata, dict):
        raise ValueError('Frontmatter is not a mapping')
    return metadata, text[m.end():]


def strip_mdx(text: str) -> str:
    """Conservative MVP text extraction, NOT a complete MDX/JSX parser.

    Removes import/export and simple JSX tags. It can miss content rendered by
    custom components; review extracted chunks before using in production.
    """
    text = re.sub(r'^\s*(?:import|export)\s+.*$', '', text, flags=re.M)
    text = re.sub(r'\{\/\*[\s\S]*?\*\/\}', ' ', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'!\[([^]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'\[([^]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'\{(?:\/\*[^*]*\*\/|[^{}\n]+)\}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def doc_url(path: Path, docs: Path, meta: dict, base_url: str) -> str:
    slug = meta.get('slug')
    if isinstance(slug, str) and slug.startswith('/'):
        tail = slug.lstrip('/')
    else:
        relative = path.relative_to(docs).with_suffix('')
        parts = list(relative.parts)
        if parts[-1] in ('index', 'README'):
            parts = parts[:-1]
        tail = '/'.join(parts)
    # Docusaurus doc slugs are relative to /docs, not the site root.
    return base_url.rstrip('/') + '/docs/' + quote(tail.strip('/'), safe='/-')


# Match Docusaurus explicit heading IDs, e.g.
# ## Heading {/* #stable-id */}
EXPLICIT_HEADING_ID = re.compile(r"\s*\{/\*\s*#([A-Za-z][A-Za-z0-9_.:-]*)\s*\*/\}\s*$")
HEADING_LINE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)\s*$")
FENCE_LINE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def section_chunks(body: str, max_chars: int = 1500) -> list[tuple[str, str | None, str]]:
    """Create section-aligned chunks with *verified explicit* Docusaurus anchors.

    Auto-generated heading IDs are deliberately not guessed. A heading without
    an explicit ID falls back to the document URL. This avoids broken links for
    duplicate, custom or MDX-generated headings.
    """
    sections: list[tuple[str, str | None, str]] = []
    heading = ''
    heading_id: str | None = None
    lines: list[str] = []
    fence_char = ''
    fence_width = 0
    seen_ids: set[str] = set()

    def flush() -> None:
        text = strip_mdx('\n'.join(lines))
        if text:
            sections.append((heading, heading_id, text))

    for line in body.splitlines():
        fence = FENCE_LINE.match(line)
        if fence:
            marker = fence.group(1)
            if not fence_char:
                fence_char, fence_width = marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_width:
                fence_char, fence_width = '', 0
            lines.append(line)
            continue

        match = HEADING_LINE.match(line) if not fence_char else None
        if match:
            flush()
            raw_heading = match.group(2)
            id_match = EXPLICIT_HEADING_ID.search(raw_heading)
            heading_id = id_match.group(1) if id_match else None
            if heading_id:
                if heading_id in seen_ids:
                    raise ValueError(f'Duplicate explicit heading ID in document: {heading_id}')
                seen_ids.add(heading_id)
                raw_heading = raw_heading[:id_match.start()]
            # Remove common inline formatting for the retrieval heading label.
            heading = strip_mdx(raw_heading).strip().strip('#').strip()
            lines = []
        else:
            lines.append(line)
    flush()

    output: list[tuple[str, str | None, str]] = []
    for heading, heading_id, section in sections:
        paragraphs = re.split(r'\n\s*\n', section)
        current = ''
        for paragraph in paragraphs:
            blocks = [paragraph[i:i+max_chars] for i in range(0, len(paragraph), max_chars)]
            for block in blocks:
                if current and len(current) + len(block) + 2 > max_chars:
                    output.append((heading, heading_id, current))
                    current = ''
                current = (current + '\n\n' + block).strip()
        if current:
            output.append((heading, heading_id, current))
    return output


def chunks_from_body(body: str, max_chars: int = 1500) -> list[tuple[str, str]]:
    """Backwards-compatible two-field helper used by existing callers/tests."""
    return [(heading, text) for heading, _id, text in section_chunks(body, max_chars)]


def documents(repo: Path, base_url: str) -> list[dict]:
    docs = repo / 'docs'
    if not docs.is_dir():
        raise FileNotFoundError(f'Missing docs directory: {docs}')
    fields = [dimension['metadata_field'] for dimension in taxonomy(repo)['dimensions'].values()]
    records = []
    for path in sorted(docs.rglob('*')):
        if path.suffix not in ('.md', '.mdx'):
            continue
        fm, body = split_frontmatter(path.read_text(encoding='utf-8'))
        lifecycle = fm.get('lifecycle') or []
        if isinstance(lifecycle, str):
            lifecycle = [lifecycle]
        # archived is intentionally *indexed* and filtered at query time.
        facets = {field: (value if isinstance(value := fm.get(field, []), list) else [value]) for field in fields}
        url = doc_url(path, docs, fm, base_url)
        rel = path.relative_to(repo).as_posix()
        title = str(fm.get('title') or path.stem)
        for ix, (heading, heading_id, chunk) in enumerate(section_chunks(body)):
            cid = hashlib.sha256(f'{rel}::{ix}::{chunk}'.encode()).hexdigest()[:24]
            # The returned URL is authoritative: the React UI must not slugify headings.
            source_url = f'{url}#{quote(heading_id, safe="-_.:")}' if heading_id else url
            records.append({'id':cid, 'source':rel, 'title':title, 'heading':heading,
                            'heading_id':heading_id, 'url':source_url,
                            'text':chunk, 'facets':facets})
    return records


def taxonomy(repo: Path) -> dict:
    path = repo / 'taxonomy' / 'taxonomy.yml'
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def manifest_hash(repo: Path) -> str:
    dig = hashlib.sha256()
    for path in sorted(list((repo/'docs').rglob('*.md')) + list((repo/'docs').rglob('*.mdx')) + [repo/'taxonomy'/'taxonomy.yml']):
        dig.update(path.relative_to(repo).as_posix().encode())
        dig.update(path.read_bytes())
    return dig.hexdigest()
