// Front Matter loads this module from a workspace webview URI.
const workspace = new URL('../../', import.meta.url);
const panelStyles = `
  portfolio-taxonomy-review { display: block; padding: 4px 0 8px; overflow-wrap: anywhere; }
  portfolio-taxonomy-review .review-toolbar { display: flex; justify-content: flex-end; margin-bottom: 8px; }
  portfolio-taxonomy-review button { padding: 3px 9px; border: 1px solid var(--vscode-button-border, transparent); border-radius: 3px; background: var(--vscode-button-secondaryBackground); color: var(--vscode-button-secondaryForeground); cursor: pointer; }
  portfolio-taxonomy-review button:hover { background: var(--vscode-button-secondaryHoverBackground); }
  portfolio-taxonomy-review button:focus-visible, portfolio-taxonomy-review summary:focus-visible { outline: 1px solid var(--vscode-focusBorder); outline-offset: 2px; }
  portfolio-taxonomy-review button:disabled { opacity: .65; cursor: default; }
  portfolio-taxonomy-review h4 { margin: 14px 0 7px; font-weight: 600; }
  portfolio-taxonomy-review .review-status { padding: 6px 8px; border-left: 2px solid var(--vscode-textLink-foreground); background: var(--vscode-textBlockQuote-background); }
  portfolio-taxonomy-review .review-status[data-state="stale"] { border-color: var(--vscode-editorWarning-foreground); }
  portfolio-taxonomy-review .review-cards { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; }
  portfolio-taxonomy-review .review-cards > li, portfolio-taxonomy-review .review-report { padding: 7px 8px; border: 1px solid var(--vscode-panel-border); border-radius: 4px; }
  portfolio-taxonomy-review .review-change { display: grid; grid-template-columns: 3.6em minmax(0, 1fr); gap: 4px; margin-top: 4px; }
  portfolio-taxonomy-review .review-add { color: var(--vscode-gitDecoration-addedResourceForeground, inherit); }
  portfolio-taxonomy-review .review-remove { color: var(--vscode-gitDecoration-deletedResourceForeground, inherit); }
  portfolio-taxonomy-review details { margin-top: 5px; }
  portfolio-taxonomy-review summary { cursor: pointer; }
  portfolio-taxonomy-review details p { margin: 5px 0 0; }
  portfolio-taxonomy-review .review-report { margin-top: 12px; }
`;

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character]);
}

function workspaceUrl(relativePath) {
  return new URL(relativePath.split('/').map(encodeURIComponent).join('/'), workspace);
}

function documentPath(filePath) {
  const root = decodeURIComponent(workspace.pathname).replace(/^\/(?=[a-z]:\/)/i, '');
  const path = filePath?.replaceAll('\\', '/');
  const windows = /^[a-z]:\//i.test(root);
  if (!path || !(windows ? path.toLowerCase().startsWith(root.toLowerCase()) : path.startsWith(root))) {
    return undefined;
  }
  const relative = path.slice(root.length);
  if (/^docs\/.+\.mdx?$/i.test(relative) && !relative.split('/').some((part) => !part || part === '.' || part === '..')) {
    return relative;
  }
}

async function readResource(relativePath) {
  const response = await fetch(workspaceUrl(relativePath), {cache: 'no-store'});
  if (response.status === 404) return undefined;
  if (!response.ok) throw new Error('Workspace resource unavailable');
  return response;
}

function values(value) {
  if (Array.isArray(value)) return value;
  return typeof value === 'string' && value ? [value] : [];
}

function formatTerm(id, labels) {
  const label = labels.get(id);
  const code = `<code>${escapeHtml(id)}</code>`;
  return label ? `${escapeHtml(label)} (${code})` : code;
}

function renderChanges(review, dimensions, pending) {
  const changes = [];
  for (const dimension of Object.values(dimensions)) {
    const field = dimension.metadataField;
    const before = values(review.current_metadata?.[field]);
    const after = values(review.metadata[field]);
    const added = after.filter((id) => !before.includes(id) && !pending.has(`${dimension.id}.${id}`));
    const removed = before.filter((id) => !after.includes(id));
    if (!added.length && !removed.length) continue;
    const labels = new Map(dimension.terms.map(({id, label}) => [id, label]));
    const reason = review.selection_reasons?.[field];
    changes.push(`<li><strong>${escapeHtml(dimension.label)}</strong>
      ${added.length ? `<div class="review-change"><span class="review-add">Add</span><span>${added.map((id) => formatTerm(id, labels)).join(', ')}</span></div>` : ''}
      ${removed.length ? `<div class="review-change"><span class="review-remove">Remove</span><span>${removed.map((id) => formatTerm(id, labels)).join(', ')}</span></div>` : ''}
      ${reason ? `<details><summary>Why these changes?</summary><p>${escapeHtml(reason)}</p></details>` : ''}
    </li>`);
  }
  for (const field of ['title', 'description']) {
    const suggestion = review.page_field_suggestions?.[field];
    if (suggestion) changes.push(`<li><strong>${field === 'title' ? 'Title' : 'Description'}</strong><div>${escapeHtml(suggestion)}</div></li>`);
  }
  return changes.length ? `<ul class="review-cards">${changes.join('')}</ul>` : '<p>No changes to existing metadata values.</p>';
}

function renderProposals(proposals) {
  if (!proposals.length) return '';
  return `<h4>Proposed new terms</h4>
    <p>Use <strong>Generate draft taxonomy migration</strong> in Actions to create a draft for review. If you approve a new term, apply the migration to add it to the shared taxonomy. Then <strong>Apply reviewed taxonomy metadata</strong> can assign that term to this document.</p>
    <ul class="review-cards">${proposals.map((term) => `<li><details>
      <summary>${escapeHtml(term.label)} (<code>${escapeHtml(term.id)}</code>)</summary>
      <p>${escapeHtml(term.reason)}</p>
      ${term.evidence?.length ? `<ul>${term.evidence.map((quote) => `<li><q>${escapeHtml(quote)}</q></li>`).join('')}</ul>` : ''}
    </details></li>`).join('')}</ul>`;
}

function renderFullReport(artifact, review) {
  const fields = {...review.page_field_suggestions, ...review.metadata};
  const warnings = [...(review.warnings ?? []).map(({message}) => message), ...(artifact.global_warnings ?? [])];
  return `<details class="review-report"><summary>Full review report</summary>
    <p>Model: ${escapeHtml(artifact.model ?? 'Unknown')}</p>
    <h4>Suggested metadata</h4>
    <dl>${Object.entries(fields).map(([field, value]) => `<dt><strong>${escapeHtml(field)}</strong></dt>
      <dd>${escapeHtml(values(value).join(', ') || 'None')}</dd>
      ${review.selection_reasons?.[field] ? `<dd>${escapeHtml(review.selection_reasons[field])}</dd>` : ''}`).join('')}</dl>
    ${warnings.length ? `<h4>Validation notes</h4><ul>${warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join('')}</ul>` : ''}
  </details>`;
}

async function renderReview(file) {
  const base = `.frontmatter/taxonomy-reviews/${file.slice('docs/'.length).replace(/\.mdx?$/i, '')}.review`;
  const response = await readResource(`${base}.json`);
  if (!response) return '<p>Run <strong>Review metadata with DeepSeek</strong> in Actions, then refresh here to see the proposal.</p>';

  const artifact = await response.json();
  const review = artifact.results?.find((result) => result.file === file);
  if (!review?.metadata || artifact.errors?.length) {
    return '<p>The saved review has no usable proposal for this document. Run the review again.</p>';
  }

  const taxonomyResponse = await readResource('src/generated/taxonomy-navigation.json');
  if (!taxonomyResponse) throw new Error('Generated taxonomy unavailable');
  const {dimensions} = await taxonomyResponse.json();
  const proposals = (review.proposed_taxonomy_terms ?? []).filter(({dimension, id}) =>
    !dimensions[dimension]?.terms.some((term) => term.id === id));
  const pending = new Set(proposals.map(({dimension, id}) => `${dimension}.${id}`));

  let status = 'This saved review has no revision information. Run the review again to verify it against the current file.';
  let state = 'unknown';
  if (review.source_sha256) {
    const source = await readResource(file);
    if (!source) throw new Error('Reviewed document unavailable');
    const digest = await crypto.subtle.digest('SHA-256', await source.arrayBuffer());
    const hash = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
    state = hash === review.source_sha256 ? 'current' : 'stale';
    status = state === 'current'
      ? 'Review matches the saved document.'
      : 'The saved document changed after this review. Run the review again before applying.';
  }

  return `<p class="review-status" data-state="${state}">${escapeHtml(status)}</p>
    <h4>Suggested metadata changes</h4>
    ${renderChanges(review, dimensions, pending)}
    ${renderProposals(proposals)}
    ${renderFullReport(artifact, review)}`;
}

class TaxonomyReviewPanel extends HTMLElement {
  connectedCallback() {
    this.refresh = this.refresh.bind(this);
    this.innerHTML = `<style>${panelStyles}</style><div class="review-toolbar"><button type="button">Refresh review</button></div>
      <p role="status"></p><div></div>`;
    this.querySelector('button').addEventListener('click', this.refresh);
    void this.refresh();
  }

  async refresh() {
    const button = this.querySelector('button');
    const status = this.querySelector('[role="status"]');
    const content = this.lastElementChild;
    button.disabled = true;
    status.textContent = 'Loading saved review…';
    content.replaceChildren();
    try {
      content.innerHTML = await renderReview(this.getAttribute('file'));
      status.textContent = '';
    } catch {
      status.textContent = 'Could not load the saved review. Check the review files and refresh.';
    } finally {
      button.disabled = false;
    }
  }
}

customElements.define('portfolio-taxonomy-review', TaxonomyReviewPanel);

// Front Matter's custom panel callback is exposed on the webview global.
window.fmExternal ??= {};
window.fmExternal.getPanelView = async (metadata) => {
  const file = documentPath(metadata?.filePath ?? metadata?.articleDetails?.path);
  if (!file) return undefined;
  return {
    title: 'Taxonomy review',
    content: `<portfolio-taxonomy-review file="${escapeHtml(file)}"></portfolio-taxonomy-review>`,
  };
};
