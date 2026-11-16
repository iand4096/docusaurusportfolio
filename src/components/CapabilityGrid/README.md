# CapabilityGrid

Displays plain Markdown grids and checklists using list children and an optional `variant="checklist"` prop.

Checklist text is bold by default. Use `checklistBold={false}` to match the standard grid’s body font, size, weight and line height; plain grids are unaffected.

For bordered cards with icons and expandable details, use [CapabilityCard](../CapabilityCard/README.md) with an `items` array. The old `CapabilityGrid items={...}` interface has been removed.

See the [usage documentation and live examples](../../../docs/implementation-details/capability-grid.mdx) for props, source/rendered comparison tables, responsive behaviour, and authoring guidance.

With Docusaurus running locally, open:

<http://127.0.0.1:3000/docusaurusportfolio/docs/implementation-details/capability-grid>

Implementation: [index.jsx](./index.jsx), [component styles](./styles.module.css), and [shared layout styles](../capability-layout.module.css).
