const {createHash} = require('node:crypto');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {engines} = require('gray-matter');

const contract = '1';
const paths = {
  taxonomy: 'taxonomy/taxonomy.yml',
  glossary: 'glossary.yml',
  policies: 'taxonomy/tooltip-policies.yml',
  decisions: 'taxonomy/tooltip-decisions.json',
  definitions: 'taxonomy/definition-reviews.yml',
};
const inline = new Set(['emphasis', 'strong', 'delete']);
const containers = new Set(['root', 'blockquote', 'list', 'listItem']);
const hash = value => 'sha256:' + createHash('sha256').update(value).digest('hex');
const stable = value => Array.isArray(value) ? '[' + value.map(stable).join(',') + ']' :
  value && typeof value === 'object' ? '{' + Object.keys(value).sort().map(key =>
    JSON.stringify(key) + ':' + stable(value[key])).join(',') + '}' : JSON.stringify(value);
const fingerprint = value => hash(stable(value));
const normalise = value => value.normalize('NFC').replace(/\s+/gu, ' ').trim();
const approved = review => review?.status === 'approved' &&
  typeof review.reviewer === 'string' && Boolean(review.reviewer.trim()) &&
  typeof review.reason === 'string' && Boolean(review.reason.trim()) &&
  /^\d{4}-\d{2}-\d{2}$/.test(review.reviewed_on) &&
  !Number.isNaN(Date.parse(review.reviewed_on)) &&
  new Date(review.reviewed_on).toISOString().slice(0, 10) === review.reviewed_on;

function load(root, candidate, {strict = false, audit = false} = {}) {
  const read = key => readFileSync(path.join(root, paths[key]), 'utf8');
  const yaml = key => engines.yaml.parse(read(key));
  const taxonomy = candidate ?? yaml('taxonomy');
  const policies = yaml('policies');
  const manifest = JSON.parse(read('decisions'));
  const definitions = yaml('definitions');
  if (policies.version !== 1 || manifest.version !== 1 || definitions.version !== 1) {
    throw new Error('Unsupported taxonomy tooltip artifact version');
  }
  const technologies = taxonomy.dimensions.technologies.terms;
  const terms = new Map();
  const active = new Map();
  for (const [id, term] of Object.entries(technologies)) {
    if (term.governance.status !== 'active' || !term.description?.trim()) continue;
    const policy = Object.hasOwn(policies.terms, id) ? policies.terms[id] : undefined;
    const basis = [term.label, term.description, term.kind ?? null, term.aliases ?? [], term.governance.status];
    const currentPolicy = policy && policy.term_basis_hash === fingerprint(basis) &&
      approved(policy.review) && ['auto', 'contextual', 'explicit', 'off'].includes(policy.mode);
    const draft = policy?.review?.status === 'draft';
    if (policy && !draft && !currentPolicy && !audit) throw new Error('Invalid tooltip policy approval for ' + id);
    const mode = currentPolicy ? policy.mode : policy && !draft ? 'unreviewed' : 'legacy';
    const entry = {...term, id, policy, mode, fingerprint: fingerprint([...basis, policy ?? null])};
    const key = term.label.toLowerCase();
    if (terms.has(key)) throw new Error('Conflicting technology tooltip label ' + term.label);
    terms.set(key, entry);
    active.set(id, entry);
  }
  if (strict) for (const id of Object.keys(policies.terms)) {
    if (!active.has(id)) throw new Error('Tooltip policy references inactive technology ' + id);
  }

  for (const {term, definition} of yaml('glossary')) {
    if (!['faceted navigation', 'metadata governance'].includes(term)) continue;
    if (terms.has(term)) throw new Error('Technology label overlaps glossary tooltip ' + term);
    terms.set(term, {id: 'glossary:' + term, label: term, description: definition, glossary: true});
  }
  const labels = [...terms.values()].map(term => term.label).sort((a, b) => b.length - a.length);
  const escaped = labels.map(label => label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const pattern = escaped.length ? new RegExp(
    '(?<![\\p{L}\\p{N}_])(?:' + escaped.join('|') + ')(?![\\p{L}\\p{N}_])', 'giu',
  ) : null;
  const holds = new Set(Object.values(definitions.findings)
    .filter(finding => ['needs_review', 'confirmed_inconsistent'].includes(finding.status))
    .map(finding => finding.term_id));
  return {active, terms, pattern, manifest, definitions, holds, policies,
    taxonomyHash: fingerprint(taxonomy), policyHash: hash(read('policies'))};
}

function scan(tree, source, config) {
  const mentions = [];
  const explicit = [];
  const headings = [];
  const errors = [];
  function paragraph(node) {
    const sourcePosition = node.position;
    const context = sourcePosition ? normalise(source.slice(sourcePosition.start.offset, sourcePosition.end.offset)) : '';
    const contextHash = hash(context);
    function visitInline(parent) {
      for (const child of parent.children) {
        if (inline.has(child.type)) visitInline(child);
        if (child.type === 'mdxJsxTextElement' && child.name === 'TaxonomyTerm') {
          const [attribute] = child.attributes;
          const id = attribute?.value;
          const term = config.active.get(id);
          if (child.attributes.length !== 1 || attribute?.name !== 'id' || !term ||
              term.mode === 'off' || child.children.length !== 1 ||
              child.children[0].type !== 'text' || child.children[0].value !== term.label) {
            errors.push('Invalid explicit TaxonomyTerm at line ' + (child.position?.start.line ?? 0));
          } else {
            explicit.push({child, term});
          }
        }
        if (child.type !== 'text' || !config.pattern) continue;
        const offset = child.position?.start.offset ?? 0;
        const safe = Boolean(child.position) && source.slice(offset, child.position.end.offset) === child.value;
        for (const match of child.value.matchAll(config.pattern)) {
          const term = config.terms.get(match[0].toLowerCase());
          if (!term.glossary && term.label !== match[0]) continue;
          const start = offset + match.index;
          const range = safe ? {
            start: Buffer.byteLength(source.slice(0, start)),
            end: Buffer.byteLength(source.slice(0, start + match[0].length)),
          } : null;
          const markedContext = range && sourcePosition ?
            normalise(source.slice(sourcePosition.start.offset, start) + '[[' + match[0] + ']]' +
              source.slice(start + match[0].length, sourcePosition.end.offset)) : null;
          mentions.push({child, term, index: match.index, text: match[0], range, context, markedContext,
            contextHash, headings: [...headings], line: (child.position?.start.line ?? 0)});
        }
      }
    }
    visitInline(node);
  }
  function visit(node) {
    if (node.type === 'heading') {
      headings.length = node.depth - 1;
      headings.push(node.children.map(child => child.value ?? '').join(''));
    } else if (node.type === 'paragraph') paragraph(node);
    else if (containers.has(node.type)) node.children.forEach(visit);
  }
  visit(tree);
  const eligible = new Set(explicit.map(item => item.child));
  function checkExplicit(node) {
    if (['mdxJsxTextElement', 'mdxJsxFlowElement'].includes(node.type) &&
        node.name === 'TaxonomyTerm' && !eligible.has(node)) {
      errors.push('Invalid or ineligible explicit TaxonomyTerm at line ' + (node.position?.start.line ?? 0));
    }
    node.children?.forEach(checkExplicit);
  }
  checkExplicit(tree);
  return {mentions, explicit, errors};
}

function decisionKey(decision) {
  return stable([decision.term_id, decision.term_fingerprint, decision.matched_text,
    decision.source_range, decision.context_hash]);
}

function indexDecisions(manifest, document, source) {
  const entry = manifest.documents[document];
  if (manifest.matching_contract_version !== contract || entry?.content_hash !== hash(source)) return new Map();
  const index = new Map();
  for (const decision of entry.decisions) {
    const key = decisionKey(decision);
    index.set(key, index.has(key) ? null : decision);
  }
  return index;
}

function occurrence(mention) {
  return {term_id: mention.term.id, term_fingerprint: mention.term.fingerprint,
    matched_text: mention.text, source_range: mention.range, context_hash: mention.contextHash};
}

function reviewedDecision(decisions, mention) {
  if (!mention.range) return undefined;
  const decision = decisions.get(decisionKey(occurrence(mention)));
  return approved(decision?.review) && ['accept', 'reject'].includes(decision.result) ? decision : undefined;
}

module.exports = {contract, paths, hash, fingerprint, normalise, approved, load, scan,
  indexDecisions, occurrence, decisionKey, reviewedDecision};
