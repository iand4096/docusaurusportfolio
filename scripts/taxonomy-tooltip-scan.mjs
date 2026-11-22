import fs from 'node:fs';
import path from 'node:path';
import {unified} from 'unified';
import parse from 'remark-parse';
import mdx from 'remark-mdx';
import gfm from 'remark-gfm';
import frontmatter from 'remark-frontmatter';
import directive from 'remark-directive';
import matter from 'gray-matter';
import matching from '../plugins/taxonomy-tooltip-matching.cjs';

process.stdin.setEncoding('utf8');
const inputChunks = [];
for await (const chunk of process.stdin) inputChunks.push(chunk);
const input = JSON.parse(inputChunks.join(''));
const config = matching.load(input.root, input.candidate, {strict: input.strict, audit: !input.strict});
const parser = unified().use(parse).use(frontmatter).use(mdx).use(gfm).use(directive);
const documents = {};
const errors = [];
for (const file of input.files) {
  const absolute = fs.realpathSync(path.resolve(input.root, file));
  if (!absolute.startsWith(fs.realpathSync(path.join(input.root, 'docs')) + path.sep)) {
    throw new Error('Tooltip scan path is outside docs: ' + file);
  }
  const source = input.overrides?.[file] ?? fs.readFileSync(absolute, 'utf8');
  if (Buffer.byteLength(source) > 2_000_000) throw new Error('Tooltip document exceeds size limit: ' + file);
  const {mentions, errors: markupErrors} = matching.scan(parser.parse(source), source, config);
  errors.push(...markupErrors.map(error => file + ': ' + error));
  const decisions = matching.indexDecisions(config.manifest, file, source);
  const matched = new Set();
  const first = new Set();
  const candidates = [];
  for (const mention of mentions) {
    if (mention.term.glossary) continue;
    const occurrence = matching.occurrence(mention);
    const decision = matching.reviewedDecision(decisions, mention);
    if (decision) matched.add(matching.decisionKey(decision));
    // Require decisions for the configured label and enabled aliases in their registered casing.
    // Additional case variants can be reviewed without blocking the build.
    if (input.strict && mention.term.mode === 'contextual' &&
        (mention.text === mention.term.label || mention.term.enabledAliases.includes(mention.text)) && !decision) {
      errors.push(file + ':' + mention.line + ': contextual tooltip needs review for ' + mention.term.id);
    }
    const eligible = ['legacy', 'auto'].includes(mention.term.mode) ||
      (mention.term.mode === 'contextual' && decision?.result === 'accept' && !config.holds.has(mention.term.id));
    const firstEligible = eligible && !first.has(mention.term.id);
    if (eligible) first.add(mention.term.id);
    candidates.push({...occurrence, label: mention.term.label, line: mention.line,
      context: mention.context, marked_context: mention.markedContext, headings: mention.headings, policy: mention.term.mode,
      first_eligible: firstEligible, current_decision: decision ?? null});
  }
  const staleDecisions = [];
  for (const decision of config.manifest.documents[file]?.decisions ?? []) {
    if (!matched.has(matching.decisionKey(decision)) || config.active.get(decision.term_id)?.mode !== 'contextual') {
      staleDecisions.push(decision);
      if (input.strict) errors.push(file + ': stale or inapplicable tooltip decision for ' + decision.term_id);
    }
  }
  documents[file] = {content_hash: matching.hash(source),
    technologies: matter(source).data.technologies ?? [], candidates, stale_decisions: staleDecisions};
}
for (const file of Object.keys(config.manifest.documents)) {
  if (input.strict && !input.files.includes(file)) errors.push('Unknown tooltip decision document ' + file);
}
console.log(JSON.stringify({version: 1, matching_contract_version: matching.contract,
  taxonomy_hash: config.taxonomyHash, policy_hash: config.policyHash, documents, errors,
  policies: config.policies.terms,
  terms: Object.fromEntries([...config.active].map(([id, term]) => [id, {
    id, label: term.label, description: term.description, kind: term.kind,
    definition_hash: matching.fingerprint(term.description),
    term_basis_hash: matching.fingerprint([term.label, term.description, term.kind ?? null,
      term.aliases ?? [], term.governance.status]),
  }]))}));
