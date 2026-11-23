const fs = require('node:fs/promises');
const path = require('node:path');
const {isDeepStrictEqual} = require('node:util');
const {markdownParser, operationAnchor, walk} = require('../plugins/markdown-exports.cjs');
const spec = require('../static/api/search-openapi.json');

const site = new URL('https://iand4096.github.io/docusaurusportfolio/');
const outDir = path.resolve(process.argv[2] || 'build');
const caseStudies = [
  'docs/case-studies/DocusaurusPortfolio.md',
  'docs/case-studies/RagSearchCloudArchitecture.md',
  'docs/case-studies/documentation-qa.md',
];

const searchOperation = spec.paths['/search'].post;
const exampleName = 'taxonomy-filter';
const expectedPayloads = [
  searchOperation.requestBody.content['application/json'].examples[exampleName].value,
  searchOperation.responses['200'].content['application/json'].examples[exampleName].value,
];

const scalarAnchors = new Set(Object.values(spec.paths).flatMap(entry =>
  Object.values(entry).filter(operation => operation.operationId && operation.tags?.length)
    .map(operation => operationAnchor(operation.operationId)),
));

async function findTarget(relative) {
  const filename = path.resolve(outDir, relative);
  if (filename !== outDir && !filename.startsWith(outDir + path.sep)) return undefined;
  for (const candidate of [filename, path.join(filename, 'index.html'), filename + '.html']) {
    try {
      if ((await fs.stat(candidate)).isFile()) return candidate;
    } catch (error) {
      if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') throw error;
    }
  }
}

async function linkProblem(destination) {
  let url;
  try {
    url = new URL(destination);
  } catch {
    return 'expected an absolute URL';
  }
  if (url.protocol === 'mailto:' || url.protocol === 'tel:') return;
  if (url.protocol !== 'https:' && url.protocol !== 'http:') return 'unsupported URL scheme';
  if (url.origin !== site.origin) return;
  if (!url.pathname.startsWith(site.pathname)) return 'URL is outside the published site base path';

  const relative = decodeURIComponent(url.pathname.slice(site.pathname.length));
  const target = await findTarget(relative);
  if (!target) return 'target is missing from the publish directory';

  if (url.hash && target.endsWith('.html')) {
    const anchor = decodeURIComponent(url.hash.slice(1));
    if (relative === 'search-api' && scalarAnchors.has(anchor)) return;
    const html = await fs.readFile(target, 'utf8');
    const anchors = Array.from(html.matchAll(/\s(?:id|name)=(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g),
      match => match[1] ?? match[2] ?? match[3]);
    if (!anchors.includes(anchor)) return 'anchor is missing from the target HTML';
  }
}

async function main() {
  const parser = await markdownParser();
  const errors = [];
  const checkedLinks = new Map();
  const aggregate = 'llms-full.txt';
  for (const file of [...caseStudies, 'llms.txt', aggregate]) {
    const content = await fs.readFile(path.join(outDir, file), 'utf8');
    const tree = parser.parse(content);
    const links = [];
    const payloads = [];
    walk(tree, node => {
      if (['link', 'image', 'definition'].includes(node.type)) links.push(node);
      if (node.type === 'code' && node.lang === 'json') {
        try {
          payloads.push(JSON.parse(node.value));
        } catch {
          // Other sections can contain illustrative JSON fragments.
        }
      }
    });
    if (file.endsWith('RagSearchCloudArchitecture.md') || file === aggregate) {
      if (!expectedPayloads.every(expected => payloads.some(payload => isDeepStrictEqual(payload, expected)))) {
        errors.push(`${file}: missing the OpenAPI taxonomy-filter request or HTTP 200 response JSON block`);
      }
    }
    for (const {url, position} of links) {
      if (!checkedLinks.has(url)) checkedLinks.set(url, await linkProblem(url));
      const problem = checkedLinks.get(url);
      if (problem) errors.push(`${file}:${position.start.line}: ${problem}: ${url}`);
    }
  }
  if (errors.length) throw new Error(errors.join('\n'));
  console.log('Verified case study exports, LLM files, OpenAPI example payloads and local link destinations.');
}

main().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
