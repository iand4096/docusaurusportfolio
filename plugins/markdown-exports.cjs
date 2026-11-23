const fs = require('node:fs/promises');
const {existsSync} = require('node:fs');
const path = require('node:path');
const spec = require('../static/api/search-openapi.json');

const operations = new Map(
  Object.values(spec.paths).flatMap(entry => Object.values(entry))
    .filter(operation => operation.operationId)
    .map(operation => [operation.operationId, operation]),
);

function operationAnchor(operationId) {
  const tag = operations.get(operationId)?.tags?.[0];
  if (!tag) throw new Error(`OpenAPI operation has no reference link: ${operationId}`);
  return `tag/${tag.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-')}/${operationId}`;
}

async function markdownParser() {
  const [{unified}, {default: remarkParse}, {default: remarkGfm}, {default: frontmatter}] =
    await Promise.all(['unified', 'remark-parse', 'remark-gfm', 'remark-frontmatter'].map(name => import(name)));
  return unified().use(remarkParse).use(remarkGfm).use(frontmatter);
}

function walk(node, visit) {
  visit(node);
  for (const child of node.children || []) walk(child, visit);
}

function applyEdits(content, edits) {
  for (const {start, end, value} of edits.sort((a, b) => b.start - a.start)) {
    content = content.slice(0, start) + value + content.slice(end);
  }
  return content;
}

function serializeApiExamples(content, parser, baseUrl) {
  if (!content.includes('<ApiExample') && !content.includes('<ApiEndpoint')) return content;
  const protectedRanges = [];
  walk(parser.parse(content), node => {
    if (node.type === 'code' || node.type === 'inlineCode') protectedRanges.push(node.position);
  });
  const edits = [];
  for (const match of content.matchAll(/<(ApiExample|ApiEndpoint)\s+([^<>]*?)\/>/g)) {
    const start = match.index;
    if (protectedRanges.some(({start: from, end}) => start >= from.offset && start < end.offset)) continue;
    const [, component, attrs] = match;
    const operationId = /\boperationId="([^"]+)"/.exec(attrs)?.[1];
    const operation = operations.get(operationId);
    if (!operation) throw new Error(`Unknown OpenAPI operation in Markdown export: ${operationId}`);
    const reference = `${baseUrl}search-api#${operationAnchor(operationId)}`;
    let value = `[${operationId}](${reference})`;
    if (component === 'ApiExample') {
      const example = /\bexample="([^"]+)"/.exec(attrs)?.[1];
      const status = /\bstatus=\{(\d+)\}/.exec(attrs)?.[1] ?? '200';
      const language = /\blanguage="([^"]+)"/.exec(attrs)?.[1];
      if (language || content.slice(content.lastIndexOf('\n', start - 1) + 1, start).trim()) {
        value = `[OpenAPI example: ${example}](${reference})`;
      } else {
        const request = operation.requestBody?.content?.['application/json']?.examples?.[example];
        const response = operation.responses?.[status]?.content?.['application/json']?.examples?.[example];
        if (!request || !response) throw new Error(`Missing OpenAPI payload for ${operationId}/${example} (HTTP ${status})`);
        const block = data => '```json\n' + JSON.stringify(data.value, null, 2) + '\n```';
        value = `**Request**\n\n${block(request)}\n\n**Response (HTTP ${status})**\n\n${block(response)}`;
      }
    }
    edits.push({start, end: start + match[0].length, value});
  }
  return applyEdits(content, edits);
}

function createLinkRewriter(siteConfig, siteDir, docs, exported) {
  const bySource = new Map(docs.map(doc => [doc.source.replace(/^@site\//, ''), doc]));
  const byRoute = new Map(docs.map(doc => [doc.permalink, doc]));
  return (destination, current) => {
    if (destination.startsWith('//')) return `https:${destination}`;
    if (/^[a-z][\w+.-]*:/i.test(destination) && !destination.startsWith('pathname:///')) {
      return destination;
    }
    const [, target, suffix] = /^([^?#]*)(.*)$/s.exec(destination);
    const hasFragment = suffix.includes('#');
    const {baseUrl, url} = siteConfig;
    let route;
    if (!target && current) {
      route = current.permalink;
    } else if (target.startsWith('pathname:///')) {
      route = baseUrl + target.slice('pathname:///'.length);
    } else if (target.startsWith('/')) {
      route = target.startsWith(baseUrl) ? target : baseUrl + target.slice(1);
    } else if (current && target) {
      const relativeSource = path.posix.join(path.posix.dirname(current.source.replace(/^@site\//, '')), decodeURI(target));
      const doc = bySource.get(relativeSource);
      if (doc) {
        route = doc.permalink;
      } else if (!relativeSource.startsWith('../') && existsSync(path.join(siteDir, relativeSource))) {
        const repoPath = relativeSource.split('/').map(encodeURIComponent).join('/');
        return `https://github.com/${siteConfig.organizationName}/${siteConfig.projectName}/blob/main/${repoPath}${suffix}`;
      } else {
        route = new URL(target, new URL(current.permalink, url)).pathname;
      }
    } else {
      return destination;
    }
    // Markdown exports have no Docusaurus heading IDs, so section links use the rendered page.
    if (!hasFragment && byRoute.has(route) && exported.has(route)) route += '.md';
    return new URL(route + suffix, url).href;
  };
}

function rewriteMarkdownLinks(content, parser, rewrite, current, docsByTitle) {
  const edits = [];
  const tree = parser.parse(content);
  for (const section of tree.children) {
    if (docsByTitle && section.type === 'heading' && section.depth === 2) {
      const {start, end} = section.position;
      // The LLM corpus places each document under a heading named for its title.
      current = docsByTitle.get(content.slice(start.offset + 3, end.offset)) || current;
    }
    walk(section, node => {
      if (!['link', 'image', 'definition'].includes(node.type)) return;
      const value = rewrite(node.url, current);
      if (value === node.url) return;
      const {start, end} = node.position;
      const raw = content.slice(start.offset, end.offset);
      // Work on the destination only. This preserves link labels, titles and surrounding Markdown.
      const range = node.type === 'definition'
        ? /^(\[[^\n]+?\]:\s*)<?([^\s>]+)>?/.exec(raw)
        : /^(.*\]\(\s*)<?([^\s>]+?)>?(?=\s|\)$)/s.exec(raw);
      if (!range) return;
      const destinationStart = start.offset + range[1].length;
      edits.push({start: destinationStart, end: start.offset + range[0].length, value: `<${value}>`});
    });
  }
  return applyEdits(content, edits);
}

async function processMarkdownExports({siteConfig, siteDir, outDir, docs, serialize, fullFilename}) {
  const parser = await markdownParser();
  const exported = new Set();
  const files = new Map();
  for (const doc of docs) {
    const relative = decodeURI(doc.permalink.slice(siteConfig.baseUrl.length));
    const filename = path.join(outDir, `${relative}.md`);
    try {
      files.set(doc, {filename, content: await fs.readFile(filename, 'utf8')});
      exported.add(doc.permalink);
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
  }
  const rewrite = createLinkRewriter(siteConfig, siteDir, docs, exported);
  const transform = content => serializeApiExamples(serialize(content), parser, siteConfig.baseUrl);
  for (const [doc, {filename, content}] of files) {
    const updated = rewriteMarkdownLinks(transform(content), parser, rewrite, doc);
    if (updated !== content) await fs.writeFile(filename, updated);
  }
  const fullPath = path.join(outDir, fullFilename);
  const aggregate = await fs.readFile(fullPath, 'utf8');
  const docsByTitle = new Map(docs.map(doc => [doc.title.replace(/\s+/g, ' ').trim(), doc]));
  await fs.writeFile(fullPath, rewriteMarkdownLinks(transform(aggregate), parser, rewrite, undefined, docsByTitle));
}

module.exports = {markdownParser, operationAnchor, processMarkdownExports, walk};
