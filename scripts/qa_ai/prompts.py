"""Shared AI review instructions and response contracts."""

COMMON_AI_RULES = r"""
Use British English. British English does not mandate omitting serial commas.
Report punctuation consistency only against an explicit supplied style rule or
verified comparison passages; do not infer a rule from nationality.
Preserve official product names even when their spelling differs from house style.
Clear contractions and capability-list fragments are acceptable. Coordinated verbs
sharing a subject (including an understood subject in a list) are not comma splices.
A generic but accurate heading is not evidence of a placeholder.


This is a defect review, not a copy-editing exercise.

Respect the DOCUMENT GENRE supplied for each file. Genre context is review
metadata, not source text and must never be quoted as an issue.
- Case studies and documentation samples may explain the author's contribution,
  decisions and available evidence. Do not require metrics, public artefacts or
  confidential details, or turn every paragraph into a problem/outcome statement.
- Skills and tools overviews are concise capability inventories, not case studies.
  Named techniques, technologies, responsibilities and short examples are valid.
  Do not require a problem, stakeholder, outcome, ownership statement or evidence
  link for every capability. Related software engineering, QA and personal learning
  experience is legitimate when accurately labelled; do not force a documentation
  outcome onto it. Evidence may live in a linked case study.
- Technical READMEs, component guides, implementation guides and operations
  runbooks serve users and maintainers. Review procedural accuracy, prerequisites,
  clarity and navigation, not portfolio storytelling, personal ownership or impact.
  Necessary warnings may be repeated at the point where an operation is performed.
- Landing pages and the homepage introduce and route readers to other pages.
  Short summaries and product context are appropriate; do not demand a complete
  case study inside a navigation card.
- For other documents, assess their stated purpose without imposing a case-study
  template. Site-wide comparisons must respect differences between genres.
All genres remain eligible for genuine language, clarity and consistency defects.
Useful product context is not a defect merely because it describes the product.
First-person attribution is appropriate in a personal portfolio, including READMEs.
Do not rewrite software testing as documentation validation unless the source
establishes that purpose. Do not invent implementation scope to fill perceived gaps.
Do not diagnose malformed JSX/HTML from an excerpt or a partial quotation.
Markup syntax belongs to deterministic parser/build checks, not this prose review.

The supplied documents are editorial review views, not complete raw source.
Within YAML front matter, only reader-facing prose is retained. Technical fields
are deliberately replaced by spaces while preserving source positions and the
opening/closing delimiters. Blank lines and incomplete-looking YAML structures
inside that block are filtering artefacts, not evidence of unfinished content.
Review the retained metadata values for prose quality only. Do not report YAML
syntax, missing metadata, placeholders or unfinished content based on masked
front matter. The Markdown/MDX body after the closing delimiter is unchanged.

Be conservative. Report only meaningful issues. The expected result for a
professionally written page is often ZERO issues. Do not manufacture a finding
merely because you were asked to review the page.
NEVER report an issue solely because:
- wording could be shorter, smoother, punchier or more elegant
- another writer might choose different wording
- a sentence could be split or combined without materially improving comprehension
- active voice might be preferable to passive voice
- a heading could be phrased differently while remaining accurate
- paragraph or sentence length is merely a stylistic preference
- information could theoretically be presented as bullets
- terminology is unusual but clear and internally consistent
- the prose does not match your preferred writing style
A stylistic preference is NOT a defect.

Before reporting any issue, verify all three conditions:
1. There is a concrete problem in the supplied text.
2. You can explain a material reader impact.
3. The proposed change is more than a stylistic alternative.
If any condition is not satisfied, DO NOT report the issue.
Do not:
- invent facts, responsibilities, metrics, audiences, outcomes, technical
  relationships or source text
- claim technical information is incorrect unless the supplied text itself
  demonstrates the inconsistency
- include the artificial line-number prefix in the quoted source text

Every issue must also provide:
- reader_impact: a concrete consequence, not a preference or restatement
- evidence: a list of {"file": "supplied file path", "quote": "verbatim passage"}
- rule_basis: the applicable grammar rule, explicit style rule or structural reason
For repetition and consistency, include at least two distinct supporting passages.
Explain why their purposes overlap: topic similarity alone is insufficient.
Never report a finding whose explanation concedes no problem, whose correction
repeats the original, or whose suggestion introduces unsupported facts.

Every issue must include exact source text copied verbatim from the supplied
file in "original". The quoted text must be sufficient to identify the issue.
Do not paraphrase "original".
Severity is strict and means impact:
- high: never permitted for AI-origin findings; use medium at most
- medium: a substantive problem that materially impairs comprehension or correctness
- low: a worthwhile non-blocking improvement

Never assign high severity to any finding.
Do not report heading-capitalisation-only issues; Vale checks heading case.
Never assign high or medium severity to a purely stylistic improvement.
Improvements and diagram opportunities should normally be low severity.
Confidence means certainty that the issue is genuinely present:
- high: objectively demonstrated by the supplied text
- medium: well supported but includes editorial judgement
- low: subjective or weakly supported

Omit low-confidence findings unless they identify a clear concrete risk.

Use issue type:
- defect: something is objectively or substantively wrong
- improvement: optional editorial or information-design improvement
- diagram: optional Mermaid visualisation opportunity
Return JSON only. Do not include Markdown fences or commentary.
"""

SUBSTANTIVE_DEFECT_RULES = r"""
REVIEW INTENT: substantive defects only. This instruction takes priority over
check-specific invitations to suggest improvements. Return only type "defect".
Do not report repetition, scannability, portfolio presentation or diagram
opportunities unless there is a demonstrated substantive failure.
A finding must establish a wrong instruction, contradiction, missing prerequisite,
broken reference, genuinely ambiguous meaning or objectively incorrect language.
Preserve a reasonable conventional reading. Mere potential hesitation, minor
stylistic inconsistency or a different possible phrasing is insufficient.
For ambiguity, identify two plausible interpretations and the materially different
consequences. For consistency, identify the explicit violated rule or conflicting
instructions; do not infer a rule from nationality or a preferred style.
Do not require a minimum number of findings. Zero is a successful review.

Negative examples from withdrawn findings:
- "Wrote the guide, during my first few months at Mastercard, developed the test
  integration and created diagrams" uses shared-subject coordinated verbs and a
  comma-delimited parenthetical. Parentheses are optional; do not call it a run-on.
- A component accepts type="decision" but displays "Decision". A prose colour note
  naming the display label does not contradict the lowercase API value.
These are reasoning examples, not blanket exemptions for future changed sources.
"""

DEFECT_VERIFICATION_CONTRACT = r"""
First explain the strongest reasonable, conventional reading of the original.
Try to refute the allegation using the complete source before accepting it.
For every supported assessment also return:
- substantive_defect: boolean (false for preferences or speculative harm)
For substantive_defect=true, additionally return nonempty strings:
- reasonable_reading: the strongest defensible reading of the original
- why_reading_fails: source-grounded explanation of why that reading still fails
- consequence: the concrete failure affecting the reader
- failure_kind: wrong_instruction, contradiction, missing_prerequisite,
  broken_reference, ambiguous_meaning or incorrect_language
For failure_kind=ambiguous_meaning also return interpretations: exactly two
nonempty strings identifying plausible meanings with materially different outcomes.
A claim of possible confusion without those meanings is insufficient.
Do not approve a finding merely because its proposed alternative is also valid.
"""

PAGE_JSON_CONTRACT = r"""
Return exactly this structure:
{
  "issues": [
    {
      "severity": "medium|low",
      "confidence": "high|medium|low",
      "type": "defect|improvement|diagram",
      "category": "CATEGORY_FROM_THIS_CHECK",
      "line": 12,
      "original": "exact source text",
      "reader_impact": "Concrete reader consequence",
      "evidence": [{"file": "docs/example.mdx", "quote": "exact supporting source text"}],
      "rule_basis": "Applicable rule or structural reason",
      "message": "Concise explanation of the problem",
      "suggestion": "Specific suggested correction or improvement",
      "source": "ai"
    }
  ]
}

Return {"issues": []} when there are no meaningful findings.
"""
SITE_JSON_CONTRACT = r"""
Return exactly this structure:
{
  "issues": [
    {
      "file": "docs/example.mdx",
      "severity": "medium|low",
      "confidence": "high|medium|low",
      "type": "defect|improvement|diagram",
      "category": "CATEGORY_FROM_THIS_CHECK",
      "line": 12,
      "original": "exact source text copied from the named file",
      "reader_impact": "Concrete reader consequence",
      "evidence": [{"file": "docs/example.mdx", "quote": "exact supporting source text"}],
      "rule_basis": "Applicable rule or structural reason",
      "message": "Concise explanation of the site-wide problem",
      "suggestion": "Specific suggested correction or improvement",
      "source": "ai"
    }
  ]
}
The "file" value must exactly match one of the FILE values supplied in the
user message.

Return {"issues": []} when there are no meaningful findings.
"""
