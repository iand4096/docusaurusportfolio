"""Read-only ingestion from governed Docusaurus docs. No taxonomy mutations."""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote
import yaml

FIELDS = ('type', 'audiences', 'topics', 'technologies', 'lifecycle')


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


def chunks_from_body(body: str, max_chars: int = 1500) -> list[tuple[str, str]]:
    """Heading-aware, paragraph-aligned chunks; no tokenizer dependency."""
    sections: list[tuple[str, str]] = []
    heading = ''
    lines: list[str] = []
    for line in body.splitlines():
        if re.match(r'^#{1,6}\s+', line):
            if lines:
                sections.append((heading, '\n'.join(lines).strip()))
            heading = re.sub(r'^#{1,6}\s+', '', line).strip()
            lines = []
        else:
            lines.append(line)
    if lines:
        sections.append((heading, '\n'.join(lines).strip()))
    output = []
    for heading, section in sections:
        if not section:
            continue
        paragraphs = re.split(r'\n\s*\n', section)
        current = ''
        for paragraph in paragraphs:
            # Split unusually long paragraphs to guarantee a size bound.
            blocks = [paragraph[i:i+max_chars] for i in range(0, len(paragraph), max_chars)]
            for block in blocks:
                if current and len(current) + len(block) + 2 > max_chars:
                    output.append((heading, current))
                    current = ''
                current = (current + '\n\n' + block).strip()
        if current:
            output.append((heading, current))
    return output


def documents(repo: Path, base_url: str) -> list[dict]:
    docs = repo / 'docs'
    if not docs.is_dir():
        raise FileNotFoundError(f'Missing docs directory: {docs}')
    records = []
    for path in sorted(docs.rglob('*')):
        if path.suffix not in ('.md', '.mdx'):
            continue
        fm, body = split_frontmatter(path.read_text(encoding='utf-8'))
        lifecycle = fm.get('lifecycle') or []
        if isinstance(lifecycle, str):
            lifecycle = [lifecycle]
        # archived is intentionally *indexed* and filtered at query time.
        facets = {field: (value if isinstance(value := fm.get(field, []), list) else [value]) for field in FIELDS}
        cleaned = strip_mdx(body)
        url = doc_url(path, docs, fm, base_url)
        rel = path.relative_to(repo).as_posix()
        title = str(fm.get('title') or path.stem)
        for ix, (heading, chunk) in enumerate(chunks_from_body(cleaned)):
            cid = hashlib.sha256(f'{rel}::{ix}::{chunk}'.encode()).hexdigest()[:24]
            records.append({'id':cid, 'source':rel, 'title':title, 'heading':heading,
                            'url':url, 'text':chunk, 'facets':facets})
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
