"""Page and site-wide AI review checks."""
import json
from pathlib import Path

from qa_checks.base import BaseCheck

from . import client, verification
from .prompts import COMMON_AI_RULES, PAGE_JSON_CONTRACT, SITE_JSON_CONTRACT, SUBSTANTIVE_DEFECT_RULES
from .routing import (PORTFOLIO_REVIEW_GENRES, add_line_numbers, ai_review_content,
                      document_genre, genre_context)
from .validation import normalise_ai_issue, require_review_issues, validate_site_ai_issues

class AIPageCheck(BaseCheck):
    supports_page = True
    allowed_categories = set()
    prompt = ""

    def run_page(self, path, content, api_key):
        context = genre_context(path, content)
        genre = document_genre(path, content)
        content = ai_review_content(content)
        system_prompt = (
            COMMON_AI_RULES
            + "\n\n"
            + self.prompt
            + "\n\n"
            + (SUBSTANTIVE_DEFECT_RULES if self.defects_only else '')
            + PAGE_JSON_CONTRACT
        )
        parsed = client.request_review(
            system_prompt,
            (
                f"FILE: {path.as_posix()}\n{context}\n\n"
                f"{add_line_numbers(content)}"
            ),
            api_key,
        )

        issues = require_review_issues(parsed)

        validated = []
        for issue in issues:
            normalised = normalise_ai_issue(
                issue,
                content,
                path.as_posix(),
                self.allowed_categories,
                genre=genre,
                evidence_sources={path.as_posix(): content},
            )

            if normalised is not None:
                validated.append(normalised)

        return verification.verify_page_findings(validated, path, content, api_key, self.defects_only)

class GrammarReview(AIPageCheck):
    name = "GrammarReview"
    allowed_categories = {
        "grammar",
        "clarity",
        "consistency",
        "unfinished",
        "punctuation",
    }
    prompt = r"""
Review sentence-level editorial quality only.

Look for:
- grammar problems
- materially awkward or confusing wording
- incomplete sentences
- inconsistent terminology within the page
- unfinished or placeholder content
- punctuation or hyphenation problems that affect correctness
Do not perform general spelling checking. Spelling is checked separately.
Do not change valid British English to American English.
Do not recommend Oxford -ize spelling.
Do not flag correctly spelled technical or product terminology merely because it
is unusual.

Allowed categories:
grammar, clarity, consistency, unfinished, punctuation

Use type "defect" for genuine language/correctness problems and "improvement"
only when comprehension is materially improved.
"""

class StructureReview(AIPageCheck):
    name = "StructureReview"
    allowed_categories = {
        "structure",
        "scannability",
        "over-explanation",
    }
    prompt = r"""
Review information structure and scannability only.
Look for:
- information in an awkward order
- a paragraph doing several unrelated jobs
- important context arriving too late
- dense paragraphs that materially benefit from division
- closely related information being unnecessarily separated
- headings that do not accurately describe their content
- background explanation that materially obstructs the document's stated purpose
- important information that is unnecessarily difficult to scan
Do not add headings merely to create more sections.
Do not convert short coherent paragraphs to bullets without a clear benefit.
Do not recast a capability inventory, README or runbook as a case study.
Keep necessary operational warnings near their procedures even if summarised elsewhere.
Do not report ordinary grammar or spelling issues.

Allowed categories:
structure, scannability, over-explanation

These findings will normally use type "improvement".
"""

class PortfolioReview(AIPageCheck):
    name = "PortfolioReview"
    allowed_categories = {"portfolio"}
    prompt = r"""
Review this case study or documentation sample for a Principal Technical Writer /
Documentation Engineer portfolio, respecting its supplied DOCUMENT GENRE.
This portfolio covers both technical-writing work and documentation-engineering
work. A valid deliverable does NOT have to be a document, article, guide or other
piece of authored prose. Senior/principal-level documentation work can legitimately
produce or improve the systems through which documentation is created, governed,
tested, published, discovered and maintained.
Valid portfolio deliverables can therefore include, among other things:
- documentation portals, developer centres and documentation websites
- documentation platforms and docs-as-code architectures
- information architecture, navigation and content-model improvements
- build, publishing and deployment pipelines
- CI/CD documentation quality gates, linting and validation systems
- API-reference generation and OpenAPI-based documentation tooling
- software, API and integration testing performed to validate documentation against
  actual product or API behaviour, including examples, requests, responses, error
  handling, workflows and documented procedures
- test harnesses, scripts, fixtures or reproducible validation workflows used to
  verify documentation accuracy and prevent regressions
- search, discoverability and developer-experience improvements
- reusable components, templates and documentation design systems
- migrations between documentation platforms or toolchains
- content-management, authoring and contributor workflows
- automation, integrations and maintenance tooling
- governance, quality, observability or consistency improvements
Do not assume that personally writing a documentation artefact is inherently more
important than designing, building, migrating, automating or improving a
documentation system. Do not penalise a case study merely because its principal
deliverable is a platform, workflow, architecture, tool or engineering improvement.
Treat testing the software or API itself as relevant portfolio evidence when the
purpose is to verify that documentation, examples, procedures or reference material
match real system behaviour. This is documentation validation, not merely generic QA.
Consider whether the supplied page effectively communicates, where relevant:
- what was delivered or materially improved
- the users or stakeholders served by the work, when that context is necessary to
  understand its value; these may be documentation readers, developers,
  documentation contributors, maintainers, engineering teams or internal users
- what the author personally owned, designed, built, implemented, migrated,
  structured, automated, authored, tested, validated or otherwise contributed
- the problem, constraint or opportunity the work addressed
- what made the work useful, difficult, technically significant or operationally
  valuable
- the relationship between the portfolio description and any evidence that is
  actually available, such as a live site, repository, architecture, workflow,
  implementation, test or validation approach, generated output or published
  documentation
A contribution can be clear even when it is expressed as ownership of scope,
architecture, implementation, migration, tooling, automation, software/API
testing used to validate documentation, delivery approach or cross-functional
technical leadership. Do not require the page to separately state
that the author "wrote" an artefact when the supplied text already establishes a
credible documentation-engineering contribution.
Do not report an issue merely because a conventional technical-writer case study
might include an audience statement, list of pages written or named prose artefact.
Only report missing context when its absence materially prevents a portfolio reader
from understanding the author's contribution, the nature of the deliverable or why
the work matters.
Identify places where the page spends substantially more space explaining the
underlying product or technology than demonstrating the documentation or
documentation-engineering work.

Do not invent project results, metrics, responsibilities, audiences, business
impact, design decisions or technical facts.

If information is genuinely absent, describe only the KIND of information that
could strengthen the page. Do not fabricate the missing content.

Allowed category:
portfolio

Use type "improvement".
"""

    def run_page(self, path, content, api_key):
        if document_genre(path, content) not in PORTFOLIO_REVIEW_GENRES:
            return []
        return super().run_page(path, content, api_key)

class DiagramReview(AIPageCheck):
    name = "DiagramReview"
    allowed_categories = {"diagram"}
    prompt = r"""
Look very sparingly for Mermaid diagram opportunities.

A diagram is appropriate only when the supplied text describes something that
would be substantially easier to understand visually, such as:
- a sequence of interactions
- an API workflow
- a lifecycle
- a transformation
- relationships among several systems or components
- a decision process
- a non-obvious hierarchy
Do not suggest a diagram:
- merely to make the page more visual
- for a simple definition or fact
- for an already-clear list
- when the diagram would just repeat one or two straightforward sentences
- when the diagram would require invented technical relationships

Prefer ZERO findings for most short pages.
Return no more than ONE issue.

Allowed category:
diagram
Every finding must use severity "low" and type "diagram".
The suggestion should name the simplest appropriate Mermaid diagram type and
briefly describe what it should show. Include Mermaid source only when every
node and relationship is directly supported by the supplied text.
"""


class RepetitionReview(BaseCheck):
    name = "RepetitionReview"
    supports_page = True
    supports_site = True
    allowed_categories = {"repetition"}
    PAGE_PROMPT = r"""
Review only for unnecessary repetition within this page.

Preserve overview/detail, approach/outcome, prose/diagram, label/explanation,
standalone capability examples and warnings or checks repeated at the point of use.
Report only when the passages serve the same reader purpose and removal loses no
necessary context. Quote BOTH passages in evidence and explain that shared purpose.
Do not assume a reader consumes the whole page sequentially.

Flag repetition when:
- two passages communicate substantially the same information
- a later sentence repeats something the reader has already understood
- several sentences could be consolidated without losing useful meaning
- terminology is repeatedly re-explained after it has been established
Do not flag intentional repetition needed for clarity, repeated product names,
or passages merely because they concern the same broad subject.

Allowed category:
repetition

Use type "improvement" unless repetition creates a substantive contradiction.
"""

    SITE_PROMPT = r"""
Compare the supplied files only for unnecessary repetition across pages.
Look for:
- substantially identical introductions
- repeated explanations of the same concept
- repeated descriptions of the author's role
- repeated publication or repository boilerplate
- repeated background information
- repeated definitions that could be explained once elsewhere

Do not flag repetition merely because several case studies use the same product,
technology or terminology.

Only report repetition when reducing or consolidating it would materially improve
the portfolio.
For every issue, choose one file as the primary place where action should be
taken and quote exact text from that file. Mention the relevant comparison with
other supplied files in the message.

Allowed category:
repetition

Use type "improvement".
"""

    def run_page(self, path, content, api_key):
        context = genre_context(path, content)
        genre = document_genre(path, content)
        content = ai_review_content(content)
        system_prompt = (
            COMMON_AI_RULES
            + "\n\n"
            + self.PAGE_PROMPT
            + "\n\n"
            + (SUBSTANTIVE_DEFECT_RULES if self.defects_only else '')
            + PAGE_JSON_CONTRACT
        )
        parsed = client.request_review(
            system_prompt,
            f"FILE: {path.as_posix()}\n{context}\n\n{add_line_numbers(content)}",
            api_key,
        )

        issues = require_review_issues(parsed)
        validated = []

        for issue in issues:
            normalised = normalise_ai_issue(
                issue,
                content,
                path.as_posix(),
                self.allowed_categories,
                genre=genre,
                evidence_sources={path.as_posix(): content},
            )
            if normalised is not None:
                validated.append(normalised)

        return verification.verify_page_findings(validated, path, content, api_key, self.defects_only)

    def run_site(self, paths, contents, api_key):
        contexts = {path: genre_context(path, content) for path, content in contents.items()}
        genres = {path: document_genre(path, content) for path, content in contents.items()}
        contents = {path: ai_review_content(content) for path, content in contents.items()}
        sections = []

        for path in paths:
            path_string = path.as_posix()
            content = contents.get(path_string, "")

            if not content.strip():
                continue
            sections.append(
                "\n".join(
                    [
                        "=" * 72,
                        f"FILE: {path_string}",
                        contexts.get(path_string, genre_context(path, content)),
                        "=" * 72,
                        add_line_numbers(content),
                    ]
                )
            )

        if not sections:
            return []
        system_prompt = (
            COMMON_AI_RULES
            + "\n\n"
            + self.SITE_PROMPT
            + "\n\n"
            + (SUBSTANTIVE_DEFECT_RULES if self.defects_only else '')
            + SITE_JSON_CONTRACT
        )

        parsed = client.request_review(
            system_prompt,
            "Compare these files:\n\n" + "\n\n".join(sections),
            api_key,
        )

        validated = validate_site_ai_issues(
            require_review_issues(parsed),
            paths,
            contents,
            self.allowed_categories,
            genres=genres,
        )
        return verification.verify_page_findings(validated, Path("<site-review>"),
                                    json.dumps(contents, ensure_ascii=False), api_key, self.defects_only)

class SiteWideConsistencyReview(BaseCheck):
    name = "SiteWideConsistencyReview"
    supports_site = True
    allowed_categories = {"consistency", "structure", "portfolio"}

    PROMPT = r"""
Compare the supplied documentation as one Principal Technical Writer /
Documentation Engineer portfolio.
The portfolio may demonstrate both authored documentation and documentation
engineering. Treat documentation platforms, developer portals, publishing systems,
information architecture, automation, migrations, tooling, CI/CD quality systems,
API documentation infrastructure, software/API testing used to validate
documentation, reproducible documentation test workflows and contributor workflows
as legitimate portfolio deliverables alongside conventional written documentation.
Do not assume every case study should name a prose artefact the author personally
wrote. Evaluate whether each page makes the author's actual contribution and the
value of the work understandable in the context of that kind of project.

Do not perform grammar, spelling or sentence-level editing.
Do not report cross-page repetition; that is handled by another check.

Focus on meaningful site-wide inconsistencies involving:
1. Structural consistency
- comparable case studies present equivalent information in confusingly
  different locations
- one comparable page clearly establishes the author's contribution while
  another does not
- comparable information appears under materially inconsistent headings
- important information is easy to locate on some pages but buried on others

Do not demand identical templates. Some variation is appropriate.
2. Terminology consistency
- the same concept is named differently across pages in a way that could confuse
  readers

Do not report harmless stylistic variation.
3. Portfolio effectiveness
- recurring structural patterns make it difficult to compare case studies
- case studies systematically explain technology more strongly than they
  demonstrate the documentation or documentation-engineering work
- documentation-engineering case studies fail to make system ownership,
  implementation, architecture, automation, migration, documentation validation
  through software/API testing, or operational impact clear enough to understand the
  author's contribution
- information architecture could be consolidated or reorganised across the site
Do not treat variation between writing-focused and engineering-focused case studies
as inconsistency by itself. Their evidence and deliverables are expected to differ.

Do not invent missing project information. If a useful field appears absent,
describe only the kind of information that could strengthen comparable pages.

For every finding, choose one specific file as the primary action location and
quote exact text from that file. Use the message to explain the comparison with
other supplied files.
Allowed categories:
consistency, structure, portfolio

Use type "improvement" unless the inconsistency is objectively defective.
"""

    def run_site(self, paths, contents, api_key):
        contexts = {path: genre_context(path, content) for path, content in contents.items()}
        genres = {path: document_genre(path, content) for path, content in contents.items()}
        contents = {path: ai_review_content(content) for path, content in contents.items()}
        sections = []

        for path in paths:
            path_string = path.as_posix()
            content = contents.get(path_string, "")

            if not content.strip():
                continue
            sections.append(
                "\n".join(
                    [
                        "=" * 72,
                        f"FILE: {path_string}",
                        contexts.get(path_string, genre_context(path, content)),
                        "=" * 72,
                        add_line_numbers(content),
                    ]
                )
            )

        if not sections:
            return []
        system_prompt = (
            COMMON_AI_RULES
            + "\n\n"
            + self.PROMPT
            + "\n\n"
            + (SUBSTANTIVE_DEFECT_RULES if self.defects_only else '')
            + SITE_JSON_CONTRACT
        )

        parsed = client.request_review(
            system_prompt,
            "Review these files for consistency, respecting each document's genre:\n\n" + "\n\n".join(sections),
            api_key,
        )

        validated = validate_site_ai_issues(
            require_review_issues(parsed),
            paths,
            contents,
            self.allowed_categories,
            genres=genres,
        )
        return verification.verify_page_findings(validated, Path("<site-review>"),
                                    json.dumps(contents, ensure_ascii=False), api_key, self.defects_only)
