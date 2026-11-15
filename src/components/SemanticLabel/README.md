# SemanticLabel

Labels consequential statements in case studies and documentation-sample articles while preserving narrative prose. Import into a Docusaurus Markdown/MDX document:

```jsx
import SemanticLabel, {SemanticLabelGroup} from '@site/src/components/SemanticLabel';
```

```jsx
<SemanticLabel type="contribution">
  Maintained the integration guide and created sequence diagrams.
</SemanticLabel>

<SemanticLabelGroup>
  <SemanticLabel type="decision" appearance="row">
    Use one authoring project for online and print outputs.
  </SemanticLabel>
  <SemanticLabel type="rationale" appearance="row">
    Maintain shared procedures once while supporting different audiences.
  </SemanticLabel>
</SemanticLabelGroup>

<SemanticLabel type="outcome" appearance="accent">
  Reduced build time by approximately 15 minutes.
</SemanticLabel>
```

| Prop | Supported values | Default |
| --- | --- | --- |
| `type` | `decision`, `rationale`, `constraint`, `trade-off`, `risk`, `outcome`, `contribution`, `validation` | `decision` |
| `appearance` | `inline`, `row`, `accent` | `inline` |
| `children` | Required text or React/MDX content | None |

## Documentation-sample labels

| Type | Meaning | Fixed icon | Colour |
| --- | --- | --- | --- |
| `contribution` | The work you personally delivered or contributed; distinguish original authorship, maintenance and collaborative work. | `fa-pen-to-square` | Neutral |
| `validation` | How instructions, examples or API behaviour were tested or checked. | `fa-clipboard-check` | Neutral |

```jsx
<SemanticLabel type="contribution">
  Maintained the integration guide and created sequence diagrams.
</SemanticLabel>

<SemanticLabel type="validation">
  Tested checkout flows against the documented procedures.
</SemanticLabel>
```

Use these in commentary about a documentation sample. Do not imply ownership of a product's architecture when describing documentation decisions, or attribute later contributors' additions to the original author. Keep audience information in introductory prose and detailed procedures in their normal format. Replace overlapping summaries rather than adding labels that repeat them.

Unsupported values fall back to `decision` and `inline`. Labels, icons and colour classes come from a fixed internal mapping. No arbitrary classes or props are forwarded.

- **Inline:** the default for a standalone statement within narrative prose. A bold label and colon precede the text, without icons, borders or backgrounds. Do not nest the component inside a paragraph or span.
- **Row:** use two or more related statements inside `SemanticLabelGroup`. Labels occupy an 8.5rem column. Dividers appear only between adjacent rows, without a trailing rule. A group owns its outer spacing and supplies a named CSS container; rows stack when the group is 32rem wide or narrower. The 640px viewport breakpoint also stacks rows, including any used outside a group.
- **Accent:** reserve for one consequential finding or measured outcome within a subsection. A faint neutral background and semantic left border work in both themes. If a decision has a related rationale row, present both as rows in a group instead of mixing accent and row alignment. This does not replace Docusaurus admonitions.

Keep each labelled statement to one clear claim. Put detailed evidence and historical qualifications in the following prose. Use headings for subjects, short prose for context, grouped rows for decisions and reasoning, and ordinary prose or bullets for implementation detail. Do not label every paragraph or repeat the surrounding prose. Substantiate trade-offs and outcomes with the article evidence.

`SemanticLabelGroup` accepts row-label children and adds no heading, ARIA role or interactive behaviour. Keep explanatory prose outside the group.

Ordinary text, emphasis, links and MDX paragraphs are supported. The component uses generic containers and strong labels, without adding headings or interactive controls. Inline appearance is intended for prose; use rows or accents for structured block content.

Font Awesome icons reuse the site's existing stylesheet and are decorative (`aria-hidden`). Visible label text carries the meaning when icons or colour are unavailable. Semantic colours use theme variables; Decision reuses the site's blue documentation-link colour, with Infima primary as a fallback. Layout requires no state, effects or JavaScript measurements.

Case-study pilot: [Paysafe Developer Center](../../../docs/case-studies/PaysafeDeveloperCenter.md#publishing-architecture).

Documentation-sample examples: [MDES for Merchants](../../../docs/docs-samples/MDES4Merchants.md), [Masterpass](../../../docs/docs-samples/MasterpassMerchantIntegrationGuide.md), [AMX Composer](../../../docs/docs-samples/AMXInspiredSignageComposer.md), and [Paysafe.js](../../../docs/docs-samples/PaysafeDeveloperJS.md).

Run component checks with `node --test scripts/tests/semantic-label.test.cjs` and validate integration with `npm run build`.
