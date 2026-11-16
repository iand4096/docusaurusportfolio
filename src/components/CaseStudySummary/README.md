# CaseStudySummary

A server-rendered executive summary immediately below a case study’s H1. The
component uses theme colours and a two-column definition list on desktop, with
one column at viewport widths of 640px or less. It adds no duplicate document
title. Content is visible without JavaScript. After hydration, “Skip to case
study” moves focus to the first following content heading, and “Hide summaries”
collapses the overview while leaving a “Show summaries” control available. The
`case-study-summaries-hidden` local-storage preference applies to all case studies,
survives reloads and synchronizes between tabs. If storage is blocked, the control
still works for the current session. Markdown exports always retain the summary.

The TypeScript API exports `CaseStudySummaryProps`, `SummaryEvidence` and
`EvidenceItem`. Required fields are `employer`, `industry`, `projectType`,
`summary`, `role`, `scope`, `decision`, `deliverables`, `evidenceTitle` and
`evidence`. Evidence accepts one to four `{value, label, emphasis?}` entries.
Set `emphasis: "metric"` on a numerical result or quantified scope item to use the
larger accent type. Qualitative capability labels use smaller, neutral type. Use
`decisionLabel="Key approach"` for an investigative approach and `evidenceNote`
for qualifications. Independent projects use “Independent project” as employer
and a discipline as industry.

## Authoring and exports

Use a literal JSON spread in case-study MDX, as demonstrated in the six pages in
`docs/case-studies`. Keep the data in the article so the rendered component and
machine-readable version have one source. JSON property names and strings must
use double quotes. Do not pass variables, function calls or imported data to the
component: the export parser deliberately accepts JSON only and never evaluates
JavaScript.

`plugins/case-study-llms.cjs` wraps the installed LLM plugin, preserving this
component during its normal processing and awaiting its export step before
serializing summaries into prose, labelled fields and evidence lists. This
updates individual `.md` exports and `llms-full.txt`; it does not modify authored
sources. Unsupported syntax or invalid evidence fails the export rather than
silently dropping the summary. The wrapper preserves the upstream plugin’s
options and other lifecycle hooks.

Choose an evidence heading that describes the evidence: measurable results,
delivery evidence, technical coverage, implementation evidence or delivered
capabilities. Qualify historical figures and distinguish the scale of a system
from work performed by its documenter. Keep evaluation caveats visible.

Run `npm run build` followed by `npm run test:case-study-summary` to check rendered
markup, evidence variants and the actual generated Markdown exports.
