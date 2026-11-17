// Shared by the renderer, legend, Markdown exporter and tests.
const roles = Object.freeze({
  input: {label: 'Inputs', fill: '#DCE3EA', stroke: '#657789', icon: 'file-lines'},
  process: {label: 'Processing and delivery', fill: '#B8D5EA', stroke: '#406E91', icon: null},
  storage: {label: 'Stored data', fill: '#CDDCD4', stroke: '#5D796A', icon: 'database'},
  infra: {label: 'Infrastructure', fill: '#E0D9CE', stroke: '#817565', icon: 'server'},
  decision: {label: 'Decisions', fill: '#E5D9B8', stroke: '#8B7545', icon: null},
  interaction: {label: 'Human interaction', fill: '#CDD3DC', stroke: '#626F82', icon: 'user'},
  generation: {label: 'AI generation', fill: '#DCD5E4', stroke: '#78678A', icon: 'wand-magic-sparkles'},
});

// Neutral containers establish grouping; node colors carry the role semantics.
const groupStyles = Object.freeze(Object.fromEntries(Object.keys(roles).map(role =>
  [role, {fill: '#F0F2F4', stroke: '#858F9A'}])));

/** Standard Mermaid class statements select the shared color and icon. */
function prepareMermaid(source) {
  if (!/^\s*(?:flowchart|graph)\s+(?:TB|TD|BT|LR|RL)\b/m.test(source)) return source;
  const nodes = new Map();
  const groups = new Map();
  for (const [, ids, role] of source.matchAll(/^\s*class\s+([\w,-]+)\s+([\w-]+)\s*;?\s*$/gm)) {
    if (Object.hasOwn(roles, role)) {
      for (const id of ids.split(',')) nodes.set(id, role);
    } else if (role.startsWith('group-') && Object.hasOwn(groupStyles, role.slice(6))) {
      for (const id of ids.split(',')) groups.set(id, role.slice(6));
    }
  }
  if (!nodes.size && !groups.size) return source;

  let result = source;
  for (const [id, role] of nodes) {
    if (!roles[role].icon) continue;
    const escaped = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    // Quoted rectangle, diamond, cylinder and rounded labels, including
    // Mermaid Markdown strings. Explicit Font Awesome icons are overrides.
    // A quoted string keeps the optional Markdown backtick safe in minified builds.
    const label = new RegExp('\\b' + escaped + '(\\s*[\\[({]{1,2}\\s*"`?)', 'g');
    result = result.replace(label, (match, _opening, offset) => {
      const text = result.slice(offset + match.length);
      return /^(?:fa[a-z]?:fa-|<i\b)/.test(text)
        ? match : `${match}fas:fa-${roles[role].icon} `;
    });
  }
  const definitions = [...new Set(nodes.values())].map(role => {
    const {fill, stroke} = roles[role];
    return `classDef ${role} fill:${fill},stroke:${stroke},color:#1F2937,stroke-width:1.4px;`;
  });
  for (const [id, role] of groups) {
    const {fill, stroke} = groupStyles[role];
    definitions.push(`style ${id} fill:${fill},stroke:${stroke},color:#1F2937,stroke-width:1.5px;`);
  }
  return `${result.trimEnd()}\n\n${definitions.join('\n')}\n`;
}

module.exports = {roles, groupStyles, prepareMermaid};
