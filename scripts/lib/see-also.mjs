import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import matter from 'gray-matter';
import {unified} from 'unified';
import remarkParse from 'remark-parse';
import remarkMdx from 'remark-mdx';
import remarkGfm from 'remark-gfm';

export const SETTINGS = {limit: 3, threshold: 0.3, commonTermFraction: 0.65,
  employerBoost: 0.8, topicWeight: 0.4, technologyWeight: 0.6, topicRarityPower: 2, technologyRarityPower: 2,
  ignoredTopics: ['technical-writing', 'docs-as-code']};
const compare = (a, b) => a < b ? -1 : a > b ? 1 : 0;
const normalizePath = value => path.posix.normalize(value).replace(/\/$/, '') || '/';
const array = value => Array.isArray(value) ? value : [];
const parser = unified().use(remarkParse).use(remarkGfm).use(remarkMdx);

export function eligibility(document) {
  if (document.frontMatter.draft) return 'draft';
  if (document.frontMatter.unlisted) return 'unlisted';
  if (document.id.endsWith('/index') || document.path === '/' || document.path === '/docs') return 'overview';
  if (array(document.frontMatter.type).includes('landing-page')) return 'landing page';
  if (array(document.frontMatter.lifecycle).includes('archived')) return 'archived';
  return null;
}

export function validateOptions(value, knownIds, sourceId) {
  if (value === undefined) return {enabled: true, exclude: []};
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${sourceId}: see_also must be an object`);
  }
  for (const key of Object.keys(value)) {
    if (!['enabled', 'exclude'].includes(key)) throw new Error(`${sourceId}: unknown see_also option ${key}`);
  }
  if (value.enabled !== undefined && typeof value.enabled !== 'boolean') {
    throw new Error(`${sourceId}: see_also.enabled must be a boolean`);
  }
  const exclude = value.exclude === undefined ? [] : value.exclude;
  if (!Array.isArray(exclude) || exclude.some(id => typeof id !== 'string' || !knownIds.has(id))) {
    throw new Error(`${sourceId}: see_also.exclude must contain existing document IDs, without extensions or URLs`);
  }
  return {enabled: value.enabled ?? true, exclude: [...new Set(exclude)].sort(compare)};
}

/** Inspect syntax trees, excluding code, images, comments and import statements. */
export function extractLinks(body, source) {
  // HTML comments are legal in Markdown but not MDX; blank them without moving lines.
  const input = body.replace(/<!--[\s\S]*?-->/g, comment => comment.replace(/[^\n]/g, ' '))
    .replace(/<((?:https?:\/\/|mailto:)[^<>\s]+)>/g, (_, url) => `[${url}](${url})`);
  let tree;
  try { tree = parser.parse(input); }
  catch (error) { throw new Error(`${source}: cannot parse article links: ${error.message}`); }
  const definitions = new Map();
  const links = [];
  const warnings = [];
  function walk(node, visitor) {
    visitor(node);
    for (const child of node.children ?? []) walk(child, visitor);
  }
  walk(tree, node => {
    if (node.type === 'definition') definitions.set(node.identifier.toLowerCase(), node.url);
  });
  walk(tree, node => {
    const line = node.position?.start.line;
    if (node.type === 'link') links.push({url: node.url, line});
    if (node.type === 'linkReference') {
      const url = definitions.get(node.identifier.toLowerCase());
      if (url) links.push({url, line});
      else warnings.push({line, reason: `Unresolved reference link: ${node.identifier}`});
    }
    if (!['mdxJsxFlowElement', 'mdxJsxTextElement'].includes(node.type)) return;
    for (const attribute of node.attributes ?? []) {
      if (attribute.type === 'mdxJsxExpressionAttribute') {
        if (['Link', 'a'].includes(node.name)) warnings.push({line, reason: 'Dynamic link attributes require review'});
        continue;
      }
      if (!['href', 'to'].includes(attribute.name)) continue;
      if (typeof attribute.value === 'string') links.push({url: attribute.value, line});
      else {
        const expression = attribute.value?.data?.estree?.body?.[0]?.expression;
        if (expression?.type === 'Literal' && typeof expression.value === 'string') {
          links.push({url: expression.value, line});
        } else if (expression?.type === 'TemplateLiteral' && !expression.expressions.length) {
          links.push({url: expression.quasis[0].value.cooked, line});
        } else warnings.push({line, reason: `Dynamic ${attribute.name} on ${node.name ?? 'MDX element'} requires review`});
      }
    }
  });
  return {links, warnings};
}

export function createResolver(documents, config) {
  const bySource = new Map(documents.map(document => [document.source, document.id]));
  const byRoute = new Map(documents.map(document => [normalizePath(document.path), document.id]));
  const base = normalizePath(config.baseUrl ?? '/');
  const stripBase = route => base !== '/' && (route === base || route.startsWith(`${base}/`))
    ? route.slice(base.length) || '/' : route;
  const aliases = new Map();
  for (const plugin of config.plugins ?? []) {
    if (!Array.isArray(plugin) || plugin[0] !== '@docusaurus/plugin-client-redirects') continue;
    for (const redirect of plugin[1]?.redirects ?? []) {
      for (const from of [redirect.from].flat()) aliases.set(normalizePath(from), normalizePath(redirect.to));
    }
  }
  function routeId(route) {
    let current = normalizePath(stripBase(route));
    const visited = new Set();
    while (aliases.has(current) && !visited.has(current)) {
      visited.add(current);
      current = aliases.get(current);
    }
    return byRoute.get(current);
  }
  return (raw, document) => {
    if (!raw || raw.startsWith('#') || /^(mailto|tel|data|javascript):/i.test(raw)) return {};
    let url = raw.replace(/^pathname:\/\//, '');
    if (/^(https?:)?\/\//.test(url)) {
      const absolute = new URL(url, config.url);
      if (absolute.origin !== new URL(config.url).origin) return {};
      url = absolute.pathname;
    }
    try { url = decodeURIComponent(url.split(/[?#]/)[0]); }
    catch { return {warning: `Invalid encoded link: ${raw}`}; }
    const sourcePath = url.startsWith('@site/') ? url.slice(6)
      : url.startsWith('/') ? url.slice(1)
        : path.posix.normalize(path.posix.join(path.posix.dirname(document.source), url));
    for (const candidate of [sourcePath, `${sourcePath}.md`, `${sourcePath}.mdx`,
      `${sourcePath}/index.md`, `${sourcePath}/index.mdx`]) {
      if (bySource.has(candidate)) return {id: bySource.get(candidate)};
    }
    const route = url.startsWith('/') ? url
      : new URL(url, `${config.url}${document.path}`).pathname;
    const id = routeId(route) ?? routeId(`/${sourcePath.replace(/\.(md|mdx)$/, '')}`);
    if (id) return {id};
    if (path.posix.extname(url) && !/\.(md|mdx)$/.test(url)) return {}; // Linked assets aren't topics.
    if (/\.(md|mdx)$/.test(url) || route.startsWith('/docs/')) {
      return {warning: `Unresolved internal document link: ${raw}`};
    }
    return {};
  };
}

function overlap(left, right, frequencies, count, {rarityPower, sourceCoverage = false} = {}) {
  const a = new Set(left), b = new Set(right);
  const union = new Set([...a, ...b]);
  const shared = [...a].filter(term => b.has(term)).sort(compare);
  const weight = term => rarityPower
    ? (count / (frequencies.get(term) ?? 1)) ** rarityPower
    : Math.log(1 + count / (frequencies.get(term) ?? 1));
  const total = [...(sourceCoverage ? a : union)].reduce((sum, term) => sum + weight(term), 0);
  return {shared, value: total ? shared.reduce((sum, term) => sum + weight(term), 0) / total : 0};
}

export function rankCandidates(documents, dimensions, config, settings = SETTINGS) {
  const candidates = documents.filter(document => !eligibility(document));
  const primary = ['topics', 'technologies'].filter(id => dimensions[id]);
  const termsFor = (document, dimensionId) => array(document.frontMatter[dimensions[dimensionId]?.metadataField])
    .filter(term => dimensionId !== 'topics' || !settings.ignoredTopics.includes(term));
  const frequencies = Object.fromEntries(primary.map(id => {
    const counts = new Map();
    for (const document of candidates) {
      for (const term of new Set(termsFor(document, id))) {
        counts.set(term, (counts.get(term) ?? 0) + 1);
      }
    }
    return [id, counts];
  }));
  const resolve = createResolver(documents, config);
  const knownIds = new Set(documents.map(document => document.id));
  const pages = {};
  const review = [];
  for (const source of [...documents].sort((a, b) => compare(a.id, b.id))) {
    const options = validateOptions(source.frontMatter.see_also, knownIds, source.id);
    const status = eligibility(source) ?? (!options.enabled ? 'disabled by see_also.enabled' : null);
    const entry = {id: source.id, title: source.title, path: source.path, status, links: []};
    pages[source.id] = entry;
    const details = {...entry, warnings: [], excluded: [], ranked: []};
    review.push(details);
    if (status) continue;
    const parsed = extractLinks(source.body, source.source);
    details.warnings.push(...parsed.warnings);
    const linked = new Set();
    for (const link of parsed.links) {
      const result = resolve(link.url, source);
      if (result.id) linked.add(result.id);
      if (result.warning) details.warnings.push({line: link.line, reason: result.warning});
    }
    const sourceTopics = termsFor(source, 'topics');
    const minimumFrequency = Math.min(...sourceTopics.map(term => frequencies.topics?.get(term) ?? 1));
    const distinctiveTopics = sourceTopics.filter(term =>
      (frequencies.topics?.get(term) ?? 1) === minimumFrequency);
    for (const target of candidates) {
      if (target.id === source.id) continue;
      const employerField = dimensions.organisations?.metadataField;
      const sameEmployer = employerField && array(source.frontMatter[employerField])
        .some(term => array(target.frontMatter[employerField]).includes(term));
      const excluded = options.exclude.includes(target.id) ? 'frontmatter exclusion'
        : linked.has(target.id) && !sameEmployer ? 'already linked in article body' : null;
      if (excluded) { details.excluded.push({id: target.id, reason: excluded}); continue; }
      let score = 0;
      let specific = false;
      let distinctive = false;
      let sharedTechnology = false;
      const reasons = [];
      for (const dimensionId of primary) {
        const dimension = dimensions[dimensionId];
        const shared = overlap(termsFor(source, dimensionId),
          termsFor(target, dimensionId), frequencies[dimensionId], candidates.length,
          dimensionId === 'topics' ? {rarityPower: settings.topicRarityPower, sourceCoverage: true} : {rarityPower: settings.technologyRarityPower, sourceCoverage: true});
        score += shared.value * (dimensionId === 'topics' ? settings.topicWeight : settings.technologyWeight);
        for (const term of shared.shared) {
          if (dimensionId === 'topics' && distinctiveTopics.includes(term)) distinctive = true;
          if (dimensionId === 'technologies' &&
            frequencies[dimensionId].get(term) / candidates.length <= settings.commonTermFraction) sharedTechnology = true;
          if (frequencies[dimensionId].get(term) / candidates.length <= settings.commonTermFraction) specific = true;
          reasons.push(`${dimension.label}: ${dimension.terms.find(value => value.id === term)?.label ?? term} (${term})`);
        }
      }
      if (!specific) { details.excluded.push({id: target.id, reason: 'no shared specific topic or technology'}); continue; }
      if (!distinctive && !sharedTechnology && !sameEmployer) {
        details.excluded.push({id: target.id, reason: 'only secondary topics overlap; no shared distinctive topic, specific technology or employer'});
        continue;
      }
      for (const [id, boost] of [['audiences', 0.04], ['organisations', settings.employerBoost]]) {
        const dimension = dimensions[id];
        if (!dimension) continue;
        const shared = overlap(array(source.frontMatter[dimension.metadataField]),
          array(target.frontMatter[dimension.metadataField]), new Map(), 1);
        score += boost * shared.value;
        for (const term of shared.shared) reasons.push(`${dimension.label}: ${dimension.terms.find(value => value.id === term)?.label ?? term} (${term})`);
      }
      const ranked = {id: target.id, title: target.title, path: target.path,
        score: Number(score.toFixed(6)), reasons};
      if (ranked.score < settings.threshold) {
        details.excluded.push({id: target.id, reason: `below relevance threshold (${ranked.score})`});
      } else details.ranked.push(ranked);
    }
    details.ranked.sort((a, b) => b.score - a.score || compare(a.id, b.id));
    entry.links = details.ranked.slice(0, settings.limit);
    details.links = entry.links;
    details.excluded.sort((a, b) => compare(a.id, b.id));
  }
  return {pages, review};
}

async function filesUnder(directory) {
  const entries = await fs.readdir(directory, {withFileTypes: true});
  const files = await Promise.all(entries.map(entry => entry.isDirectory()
    ? filesUnder(path.join(directory, entry.name)) : [path.join(directory, entry.name)]));
  return files.flat().filter(file => /\.(md|mdx)$/.test(file) && !path.basename(file).startsWith('_')).sort(compare);
}

function documentPath(source, frontMatter, routeBasePath = 'docs') {
  let slug = frontMatter.slug;
  if (typeof slug !== 'string') {
    const parts = source.replace(/^docs\//, '').replace(/\.(md|mdx)$/, '').split('/');
    if (['index', 'readme'].includes(parts.at(-1).toLowerCase())) parts.pop();
    else if (typeof frontMatter.id === 'string') parts[parts.length - 1] = frontMatter.id;
    slug = parts.join('/');
  }
  return normalizePath(`/${routeBasePath}/${slug.replace(/^\//, '')}`);
}

export async function generate(siteDir, config, loadedDocs) {
  const catalogue = JSON.parse(await fs.readFile(path.join(siteDir, 'src/generated/taxonomy-navigation.json'), 'utf8'));
  const metadata = new Map((loadedDocs ?? []).map(doc => [doc.source.replace(/^@site\//, ''), doc]));
  const documents = [];
  const inputs = [];
  for (const file of await filesUnder(path.join(siteDir, 'docs'))) {
    const source = path.relative(siteDir, file).split(path.sep).join('/');
    const text = await fs.readFile(file, 'utf8');
    const parsed = matter(text);
    const loaded = metadata.get(source);
    let route = loaded?.permalink;
    if (route) {
      const base = normalizePath(config.baseUrl ?? '/');
      if (base !== '/' && route.startsWith(`${base}/`)) route = route.slice(base.length);
    }
    const id = source.replace(/^docs\//, '').replace(/\.(md|mdx)$/, '');
    documents.push({id, source, frontMatter: parsed.data, body: parsed.content,
      title: String(loaded?.title ?? parsed.data.title ?? id),
      path: normalizePath(route ?? documentPath(source, parsed.data))});
    inputs.push([source, text]);
  }
  const result = rankCandidates(documents, catalogue.dimensions, config);
  const inputHash = crypto.createHash('sha256').update(JSON.stringify({inputs,
    dimensions: catalogue.dimensions, settings: SETTINGS,
    site: {url: config.url, baseUrl: config.baseUrl, redirects: (config.plugins ?? []).filter(plugin => Array.isArray(plugin) && plugin[0] === '@docusaurus/plugin-client-redirects')},
  })).digest('hex');
  const index = {version: 1, inputHash, settings: SETTINGS, pages: result.pages};
  return {index, report: renderReport(index, result.review, config)};
}

const cell = text => String(text).replace(/\|/g, '\\|').replace(/\n/g, ' ');
export function renderReport(index, review, config) {
  const destination = route => new URL(`${(config.baseUrl ?? '/').replace(/\/$/, '')}${route}`, config.url).href;
  const lines = ['# Generated See also review', '', 'Generated by `npm run see-also:generate`. Do not edit this report.', '',
    `Input hash: \`${index.inputHash}\``, '',
    `Maximum links: ${index.settings.limit}; minimum score: ${index.settings.threshold}.`, '',
    `Topics contribute up to ${index.settings.topicWeight}, using inverse document frequency raised to ${index.settings.topicRarityPower} and coverage of the source page’s topics. Technologies contribute up to ${index.settings.technologyWeight}, using rarity-weighted coverage of the source page’s technologies. Additional destination topics and technologies do not dilute the match. A shared employer adds up to ${index.settings.employerBoost}; audience overlap adds up to 0.04. Employer and audience matches cannot establish relevance alone. Shared terms appearing on more than 65% of eligible pages cannot establish relevance alone.`, '',
    'Candidates must share a least-frequent source topic (including ties), a specific technology, or the source employer. Existing body links are suppressed unless the employer matches; manual exclusions always apply. Scores and eligibility can differ by direction.', '',
    `Topics ignored throughout recommendation matching and scoring: ${index.settings.ignoredTopics.map(term => `\`${term}\``).join(', ')}. They remain available as taxonomy metadata.`, '',
    'Scores order recommendations; they are not measured probabilities or retrieval-quality scores.', ''];
  for (const page of review) {
    lines.push(`## ${cell(page.title)}`, '', `Document ID: \`${page.id}\``, '');
    if (page.status) { lines.push(`Excluded from source recommendations: ${page.status}.`, ''); continue; }
    if (page.links.length) {
      lines.push('| Selected destination | Score | Matching metadata |', '|---|---:|---|');
      for (const link of page.links) lines.push(`| [${cell(link.title)}](${destination(link.path)}) — \`${link.id}\` | ${link.score} | ${cell(link.reasons.join('; '))} |`);
      lines.push('');
    } else lines.push('No suitable recommendations.', '');
    const remaining = page.ranked.slice(index.settings.limit);
    if (remaining.length) lines.push(`Other qualifying candidates: ${remaining.map(link => `\`${link.id}\` (${link.score})`).join(', ')}.`, '');
    if (page.excluded.length) {
      lines.push('<details><summary>Excluded candidates</summary>', '', '| Document ID | Reason |', '|---|---|');
      for (const item of page.excluded) lines.push(`| \`${item.id}\` | ${cell(item.reason)} |`);
      lines.push('', '</details>', '');
    }
    for (const warning of page.warnings) lines.push(`- Link review needed${warning.line ? ` at body line ${warning.line}` : ''}: ${cell(warning.reason)}`);
    if (page.warnings.length) lines.push('');
  }
  return `${lines.join('\n')}\n`;
}

export async function writeArtifacts(siteDir, result, check = false) {
  const outputs = [['src/generated/see-also.json', `${JSON.stringify(result.index, null, 2)}\n`],
    ['reports/see-also.md', result.report]];
  const stale = [];
  for (const [relative, content] of outputs) {
    const file = path.join(siteDir, relative);
    const current = await fs.readFile(file, 'utf8').catch(error => {
      if (error.code === 'ENOENT') return null;
      throw error;
    });
    if (current === content) continue;
    if (check) stale.push(relative);
    else { await fs.mkdir(path.dirname(file), {recursive: true}); await fs.writeFile(file, content); }
  }
  if (stale.length) throw new Error(`Stale See also artifacts: ${stale.join(', ')}. Run npm run see-also:generate.`);
}
