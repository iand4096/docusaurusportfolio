"""Document genre routing and the text eligible for AI review."""
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AI_PROSE_METADATA_PATHS = {
    ('title',), ('description',), ('sidebar_label',),
    ('sidebar_custom_props', 'sampleCard', 'tag'),
    ('sidebar_custom_props', 'sampleCard', 'description'),
    ('sidebar_custom_props', 'sampleCard', 'highlights'),
    ('sidebar_custom_props', 'sampleCard', 'ariaLabel'),
    ('sidebar_custom_props', 'skillCard', 'tag'),
    ('sidebar_custom_props', 'skillCard', 'description'),
    ('sidebar_custom_props', 'skillCard', 'highlights'),
    ('sidebar_custom_props', 'skillCard', 'ariaLabel'),
}


def ai_review_content(content):
    """Keep prose metadata and body verbatim, blanking other YAML at source lines."""
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != '---':
        return content
    end = next((i for i in range(1, len(lines))
                if lines[i].strip() in {'---', '...'}), None)
    if end is None:
        raise ValueError('Unterminated YAML front matter in AI review input')

    from ruamel.yaml import YAML
    from ruamel.yaml.nodes import MappingNode, ScalarNode, SequenceNode
    root = YAML(typ='safe').compose(''.join(lines[1:end]))
    metadata = ''.join(lines[1:end])
    # Mask characters rather than whole lines: a flow-style YAML mapping can
    # put an approved description and a technical identifier on the same line.
    masked = [char if char in '\r\n' else ' ' for char in metadata]

    def retain(start, stop):
        masked[start:stop] = metadata[start:stop]

    def visit(node, path=(), ancestors=()):
        if isinstance(node, MappingNode):
            for key, value in node.value:
                next_path = path + (key.value,)
                if any(allowed[:len(next_path)] == next_path for allowed in AI_PROSE_METADATA_PATHS):
                    visit(value, next_path, ancestors + (key,))
        elif path in AI_PROSE_METADATA_PATHS:
            nodes = node.value if isinstance(node, SequenceNode) else [node]
            for item in nodes:
                if isinstance(item, ScalarNode) and item.tag == 'tag:yaml.org,2002:str':
                    for key in ancestors:
                        retain(key.start_mark.index, key.end_mark.index)
                        if metadata[key.end_mark.index:key.end_mark.index + 1] == ':':
                            retain(key.end_mark.index, key.end_mark.index + 1)
                    retain(item.start_mark.index, item.end_mark.index)

    visit(root)
    return lines[0] + ''.join(masked) + lines[end] + ''.join(lines[end + 1:])


def add_line_numbers(text):
    """Add artificial line numbers for the model."""

    return "\n".join(
        f"{number:5}: {line}"
        for number, line in enumerate(text.splitlines(), start=1)
    )

def document_genre(path, content):
    """Classify review purpose from raw metadata and stable repository paths."""
    name = str(path).replace('\\', '/')
    try:
        name = Path(path).resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        pass
    # Operational/support documentation must not inherit the portfolio framing.
    if name.startswith('knowledge-api/'):
        return 'operations-guide' if Path(name).stem.upper().startswith('OPERATIONS') else 'technical-readme'
    if name.startswith('src/components/'):
        return 'component-guide'
    if name.startswith('docs/implementation-details/'):
        return 'implementation-guide'
    if Path(name).name.lower() in {'readme.md', 'readme.mdx'}:
        return 'technical-readme'
    if name == 'src/pages/index.md':
        return 'homepage'
    if re.match(r'^docs/(case-studies|docs-samples|skills|tools)/index\.mdx?$', name):
        return 'landing-page'
    for directory, genre in [('case-studies', 'case-study'), ('docs-samples', 'documentation-sample'),
                             ('skills', 'skill-overview'), ('tools', 'tool-overview')]:
        if name.startswith(f'docs/{directory}/'):
            return genre
    # Other locations may declare a genre explicitly. Never rely on model inference.
    if content.startswith('---\n') or content.startswith('---\r\n'):
        from ruamel.yaml import YAML
        lines = content.splitlines()
        end = next((i for i in range(1, len(lines)) if lines[i].strip() in {'---', '...'}), None)
        if end is not None:
            front = YAML(typ='safe').load('\n'.join(lines[1:end])) or {}
            kinds = front.get('type', []) if isinstance(front, dict) else []
            if isinstance(kinds, str):
                kinds = [kinds]
            for kind, genre in [('landing-page', 'landing-page'), ('implementation-guide', 'implementation-guide'),
                                ('case-study', 'case-study'), ('skill', 'skill-overview'),
                                ('tool', 'tool-overview'), ('doc-sample', 'documentation-sample')]:
                if kind in kinds:
                    return genre
    return 'general-document'


PORTFOLIO_REVIEW_GENRES = {'case-study', 'documentation-sample'}


def genre_context(path, content):
    return f'DOCUMENT GENRE: {document_genre(path, content)} (review context, not source)'
