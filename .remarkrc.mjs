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

const markdownPlugins = [
  // Syntax shared by repository Markdown and published Docusaurus content.
  remarkFrontmatter,
  remarkGfm,
  remarkDirective,

  // High-value structural checks only.
  remarkLintHeadingIncrement,
  remarkLintFencedCodeFlag,
  remarkLintNoEmptyUrl,
  remarkLintNoUndefinedReferences,
  remarkLintNoDuplicateDefinitions,
  remarkLintNoHiddenTableCell,
  remarkLintDirectiveUniqueAttributeName,
  remarkLintFinalNewline,
  remarkLintNoConsecutiveBlankLines,
  remarkLintNoMissingBlankLines,
];

export const mdxConfig = {
  plugins: [...markdownPlugins, remarkMdx, remarkLintMdxJsxUniqueAttributeName],
};

export default {plugins: markdownPlugins};
