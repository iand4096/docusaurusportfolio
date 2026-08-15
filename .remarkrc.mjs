import remarkDirective from 'remark-directive';
import remarkFrontmatter from 'remark-frontmatter';
import remarkGfm from 'remark-gfm';
import remarkMdx from 'remark-mdx';

import remarkLintDirectiveUniqueAttributeName from 'remark-lint-directive-unique-attribute-name';
import remarkLintFencedCodeFlag from 'remark-lint-fenced-code-flag';
import remarkLintHeadingIncrement from 'remark-lint-heading-increment';
import remarkLintMdxJsxUniqueAttributeName from 'remark-lint-mdx-jsx-unique-attribute-name';
import remarkLintNoDuplicateDefinitions from 'remark-lint-no-duplicate-definitions';
import remarkLintNoEmptyUrl from 'remark-lint-no-empty-url';
import remarkLintNoHiddenTableCell from 'remark-lint-no-hidden-table-cell';
import remarkLintNoUndefinedReferences from 'remark-lint-no-undefined-references';
import remarkLintFinalNewline from 'remark-lint-final-newline';
import remarkLintNoConsecutiveBlankLines from 'remark-lint-no-consecutive-blank-lines';
import remarkLintNoMissingBlankLines from 'remark-lint-no-missing-blank-lines';

export default {
  plugins: [
    // Docusaurus/Markdown syntax support.
    remarkFrontmatter,
    remarkGfm,
    remarkDirective,
    remarkMdx,

    // High-value structural checks only.
    remarkLintHeadingIncrement,
    remarkLintFencedCodeFlag,
    remarkLintNoEmptyUrl,
    remarkLintNoUndefinedReferences,
    remarkLintNoDuplicateDefinitions,
    remarkLintNoHiddenTableCell,
    remarkLintDirectiveUniqueAttributeName,
    remarkLintMdxJsxUniqueAttributeName,
    remarkLintFinalNewline,
    remarkLintNoConsecutiveBlankLines,
    remarkLintNoMissingBlankLines,
  ],
};