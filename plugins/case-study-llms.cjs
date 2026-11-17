const fs = require('node:fs/promises');
const path = require('node:path');
const llms = require('docusaurus-plugin-llms').default;
const {serializeDiagramFigures} = require('./diagram-figures.cjs');

function validateSummary(data) {
  for (const field of ['employer', 'industry', 'projectType', 'summary', 'role',
    'scope', 'decision', 'deliverables', 'evidenceTitle']) {
    if (typeof data?.[field] !== 'string' || !data[field].trim()) {
      throw new Error(`CaseStudySummary requires nonempty ${field}`);
    }
  }
  if (!Array.isArray(data.evidence) || data.evidence.length < 1 || data.evidence.length > 4
      || data.evidence.some(item => !item || typeof item.value !== 'string' || !item.value.trim()
        || typeof item.label !== 'string' || !item.label.trim()
        || (item.emphasis !== undefined && item.emphasis !== 'metric')
        || (item.labelStyle !== undefined && item.labelStyle !== 'note'))) {
    throw new Error('CaseStudySummary requires one to four value/label evidence items');
  }
  if (data.decisionLabel !== undefined && !['Key decision', 'Key approach'].includes(data.decisionLabel)) {
    throw new Error('Invalid CaseStudySummary decisionLabel');
  }
  if (data.evidenceNote !== undefined && typeof data.evidenceNote !== 'string') {
    throw new Error('Invalid CaseStudySummary evidenceNote');
  }
  return data;
}

function markdown(data) {
  validateSummary(data);
  // Field values are prose, never Markdown instructions or raw HTML.
  const text = value => value.replace(/\\/g, '\\\\').replace(/([`*_\[\]<>#])/g, '\\$1').replace(/\r?\n/g, ' ');
  const field = (label, value) => `**${label}:** ${text(value)}`;
  return [
    '**Project overview**',
    `${text(data.employer)} · ${text(data.industry)} · ${text(data.projectType)}`,
    text(data.summary), field('My role', data.role), field('Project scope', data.scope),
    field(data.decisionLabel || 'Key decision', data.decision), field('Deliverables', data.deliverables),
    `**${text(data.evidenceTitle)}**`,
    data.evidence.map(item => `- **${text(item.value)}** — ${text(item.label)}`).join('\n'),
    ...(data.evidenceNote ? [text(data.evidenceNote)] : []),
  ].join('\n\n');
}

/** Parse only literal JSON spreads; never evaluate source expressions. */
function serializeSummaries(content) {
  return content.split(/(?=<CaseStudySummary\b)/).map(part => {
      if (!part.startsWith('<CaseStudySummary')) return part;
      const prefix = /^<CaseStudySummary\s+\{\.\.\./.exec(part);
      if (!prefix) throw new Error('Export CaseStudySummary using a literal JSON spread');
      const start = prefix[0].length;
      let depth = 0;
      let quoted = false;
      let escaped = false;
      for (let i = start; i < part.length; i++) {
        const char = part[i];
        if (quoted) {
          if (escaped) escaped = false;
          else if (char === '\\') escaped = true;
          else if (char === '"') quoted = false;
        } else if (char === '"') quoted = true;
        else if (char === '{') depth++;
        else if (char === '}' && --depth === 0) {
          const suffix = /^\}\s*\/>/.exec(part.slice(i + 1));
          if (!suffix) throw new Error('Invalid CaseStudySummary closing tag');
          const data = JSON.parse(part.slice(start, i + 1));
          return markdown(data) + part.slice(i + 1 + suffix[0].length);
        }
      }
      throw new Error('Unclosed CaseStudySummary JSON');
    }).join('');
}

module.exports = function caseStudyLLMs(context, options) {
  const plugin = llms(context, {
    ...options,
    preserveComponents: [...new Set([...(options.preserveComponents || []), 'CaseStudySummary', 'DiagramFigure'])],
  });
  return {
    ...plugin,
    async postBuild(props) {
      // Docusaurus runs plugins concurrently. Await this plugin explicitly so
      // we always serialize after its Markdown and llms-full.txt are complete.
      await plugin.postBuild(props);
      async function visit(directory) {
        for (const entry of await fs.readdir(directory, {withFileTypes: true})) {
          const filename = path.join(directory, entry.name);
          if (entry.isDirectory()) await visit(filename);
          else if (entry.name.endsWith('.md') || /^llms.*\.txt$/.test(entry.name)) {
            const content = await fs.readFile(filename, 'utf8');
            if (content.includes('<CaseStudySummary') || content.includes('<DiagramFigure')) {
              await fs.writeFile(filename, serializeDiagramFigures(serializeSummaries(content)));
            }
          }
        }
      }
      await visit(props.outDir);
    },
  };
};
module.exports.serializeSummaries = serializeSummaries;
module.exports.validateSummary = validateSummary;
