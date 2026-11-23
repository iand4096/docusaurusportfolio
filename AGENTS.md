# Taxonomy migrations

- Use the current UTC date for new taxonomy migrations. Use the same date in the governance record, migration ID and filename.
- When correcting a historical migration date, verify it against Git history. Search for related migrations, file references and review records, and correct any inconsistent dates in the same change.

# Mermaid diagrams

- Wrap every Mermaid diagram in published documentation in `DiagramFigure`. Give each figure a caption and a stable `shareId`.
- Include `accTitle` and `accDescr` in each diagram. Use the shared palette roles consistently in the diagram and its legend.
- Follow the example in the [DiagramFigure authoring guide](docs/implementation-details/diagram-figure.mdx#authoring-and-maintenance).
