const {roles, prepareMermaid} = require('../src/components/DiagramFigure/theme.cjs');

/** Keep figure titles and keys in downloadable Markdown and search ingestion. */
function serializeDiagramFigures(content) {
  return content.replace(
    /<DiagramFigure\s+\{\.\.\.(\{[\s\S]*?\})\}\s*>([\s\S]*?)<\/DiagramFigure>/g,
    (_component, json, body) => {
      const {number, title, legend} = JSON.parse(json);
      if (!Number.isInteger(number) || number < 1 || typeof title !== 'string' || !title.trim()
        || !Array.isArray(legend) || !legend.length
        || new Set(legend.map(item => item.role)).size !== legend.length
        || legend.some(item => !Object.hasOwn(roles, item.role)
          || (item.label !== undefined && (typeof item.label !== 'string' || !item.label.trim())))) {
        throw new Error('DiagramFigure requires a positive number, title and unique valid legend roles');
      }
      const text = value => value.replace(/([\\`*_\[\]<>#])/g, '\\$1').replace(/\r?\n/g, ' ');
      const key = legend.map(({role, label}) => `- ${text(label || roles[role].label)}`).join('\n');
      const diagrams = body.trim().replace(/```mermaid\n([\s\S]*?)\n```/g,
        (_fence, source) => `\`\`\`mermaid\n${prepareMermaid(source).trimEnd()}\n\`\`\``);
      return `**Figure ${number}. ${text(title)}**\n\n${diagrams}\n\n**Colour and icon key**\n\n${key}`;
    },
  );
}

module.exports = {serializeDiagramFigures};
