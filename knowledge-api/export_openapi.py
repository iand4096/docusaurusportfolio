"""Export the FastAPI contract for the site's static API reference."""
import argparse
import json
from pathlib import Path

from app.main import app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check the committed snapshot for drift.')
    args = parser.parse_args()

    target = Path(__file__).resolve().parents[1] / 'static' / 'api' / 'search-openapi.json'
    snapshot = json.dumps(app.openapi(), indent=2, ensure_ascii=False) + '\n'
    if args.check:
        if not target.exists() or target.read_text(encoding='utf-8') != snapshot:
            parser.exit(1, 'Search OpenAPI snapshot is stale. Run python knowledge-api/export_openapi.py.\n')
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(snapshot, encoding='utf-8')


if __name__ == '__main__':
    main()
