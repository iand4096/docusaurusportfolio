const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const defaultBaseUrl = '/docusaurusportfolio/';
const sourceMeta = /^source=((?:scripts|src|plugins|knowledge-api)\/(?:[\w-]+\/)*[\w-]+\.(?:py|js|jsx|ts|tsx|cjs|mjs))#([\w-]+)$/;

function readRegion(lines, name, label) {
  const boundaries = kind => lines.flatMap((line, index) =>
    [`# docs:${kind} ${name}`, `// docs:${kind} ${name}`].includes(line.trim()) ? [index] : []);
  const starts = boundaries('start');
  const ends = boundaries('end');
  if (starts.length !== 1 || ends.length !== 1 || ends[0] <= starts[0] + 1) {
    throw new Error(`Expected one nonempty, ordered source region "${name}" in ${label}`);
  }
  const excerpt = lines.slice(starts[0] + 1, ends[0]);
  if (!excerpt.some(line => line.trim())) {
    throw new Error(`Empty source region "${name}" in ${label}`);
  }
  return {code: excerpt.join('\n'), start: starts[0] + 2, end: ends[0]};
}

function parseReference(meta) {
  const match = sourceMeta.exec(meta);
  if (!match) throw new Error(`Invalid source snippet reference: ${meta}`);
  return {relative: match[1], name: match[2]};
}

function createSnippetResolver(baseUrl = defaultBaseUrl) {
  const files = new Map();
  const resolved = new Map();

  return function resolveSnippet(meta) {
    if (resolved.has(meta)) return resolved.get(meta);
    const {relative, name} = parseReference(meta);
    const filename = path.join(root, relative);
    if (!files.has(relative)) {
      if (fs.realpathSync(filename) !== filename || !fs.statSync(filename).isFile()) {
        throw new Error(`Source snippet must reference a regular repository path: ${relative}`);
      }
      files.set(relative, fs.readFileSync(filename, 'utf8').split(/\r?\n/));
    }
    const lines = files.get(relative);
    const region = readRegion(lines, name, relative);
    const route = `${baseUrl.replace(/\/$/, '')}/source/${relative}/${name}`;
    const snippet = {
      ...region,
      relative,
      lines,
      route,
      url: `${route}#L${region.start}`,
      filename: path.basename(relative),
    };
    resolved.set(meta, snippet);
    return snippet;
  };
}

function remarkSourceSnippets({baseUrl = defaultBaseUrl} = {}) {
  return tree => {
    const resolve = createSnippetResolver(baseUrl);

    function expand(parent) {
      if (!parent.children) return;
      parent.children = parent.children.flatMap(node => {
        if (node.type !== 'code' || !node.meta?.startsWith('source=')) {
          expand(node);
          return [node];
        }
        if (node.value.trim()) throw new Error('A source snippet fence must be empty');
        const {code, url, filename} = resolve(node.meta);
        const props = {code, sourceUrl: url, filename, language: node.lang};
        return [{
          type: 'mdxJsxFlowElement',
          name: 'SourceSnippet',
          attributes: Object.entries(props).filter(([, value]) => value != null)
            .map(([name, value]) => ({type: 'mdxJsxAttribute', name, value})),
          children: [],
        }];
      });
    }

    expand(tree);
  };
}

function serializeSourceSnippets(content, resolve = createSnippetResolver()) {
  if (!content.includes('source=')) return content;
  let fence;
  let output = '';
  for (const line of content.match(/[^\n]*\n|[^\n]+$/g) || []) {
    const delimiter = /^ {0,3}(`{3,}|~{3,})([^\r\n]*)/.exec(line);
    if (!fence && delimiter) {
      const [, marker, info] = delimiter;
      const snippet = /^(\S+)\s+(source=.*)$/.exec(info.trim());
      fence = {marker, snippet};
      if (snippet) continue;
    } else if (fence) {
      const closing = delimiter && delimiter[1][0] === fence.marker[0] &&
        delimiter[1].length >= fence.marker.length && !delimiter[2].trim();
      if (closing) {
        if (fence.snippet) {
          const [, language, meta] = fence.snippet;
          const {code, url, filename} = resolve(meta);
          const length = Math.max(3, ...Array.from(code.matchAll(/`+/g), match => match[0].length + 1));
          const marker = '`'.repeat(length);
          const source = `[View source · ${filename}](${url})`;
          output += `${marker}${language}\n${code}\n${marker}\n\n${source}${line.endsWith('\n') ? '\n' : ''}`;
          fence = undefined;
          continue;
        }
        fence = undefined;
      } else if (fence.snippet) {
        if (line.trim()) throw new Error('A source snippet fence must be empty');
        continue;
      }
    }
    output += line;
  }
  if (fence?.snippet) throw new Error('Unclosed source snippet fence');
  return output;
}

function sourceSnippetPages({siteDir, siteConfig}) {
  const docs = path.join(siteDir, 'docs');

  return {
    name: 'source-snippet-pages',
    getPathsToWatch() {
      return [
        path.join(docs, '**/*.{md,mdx}'),
        ...['scripts', 'src', 'plugins', 'knowledge-api'].map(dir =>
          path.join(siteDir, dir, '**/*.{py,js,jsx,ts,tsx,cjs,mjs}')),
      ];
    },
    loadContent() {
      const resolve = createSnippetResolver(siteConfig.baseUrl);
      const pages = new Map();

      function scan(directory) {
        for (const entry of fs.readdirSync(directory, {withFileTypes: true})) {
          const filename = path.join(directory, entry.name);
          if (entry.isDirectory()) scan(filename);
          else if (entry.isFile() && /\.mdx?$/.test(entry.name)) {
            serializeSourceSnippets(fs.readFileSync(filename, 'utf8'), meta => {
              const snippet = resolve(meta);
              pages.set(snippet.route, snippet);
              return snippet;
            });
          }
        }
      }

      scan(docs);
      return [...pages.values()];
    },
    async contentLoaded({content, actions}) {
      for (const {route, relative, lines, start, end} of content) {
        const data = await actions.createData(
          `${route.replace(/[^\w.-]/g, '_')}.json`,
          JSON.stringify({relative, lines, start, end}),
        );
        actions.addRoute({
          path: route,
          exact: true,
          component: '@site/src/components/SourceSnippetPage/index.tsx',
          modules: {source: data},
        });
      }
    },
    configureWebpack() {
      return {module: {rules: [{
        test: /\.mdx?$/,
        include: docs,
        enforce: /** @type {const} */ ('pre'),
        use: [require.resolve('./source-snippet-dependencies.cjs')],
      }]}};
    },
  };
}

module.exports = {createSnippetResolver, parseReference, remarkSourceSnippets,
  serializeSourceSnippets, sourceSnippetPages};
