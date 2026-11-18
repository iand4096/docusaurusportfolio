const {roles, prepareMermaid} = require('../src/components/DiagramFigure/theme.cjs');

/** Number MDX figures in document order before Docusaurus renders the page. */
function numberDiagramFigures() {
  return tree => {
    let position = 0;
    function visit(node) {
      if (node.type === 'mdxJsxFlowElement' && node.name === 'DiagramFigure') {
        node.attributes.push({type: 'mdxJsxAttribute', name: 'figurePosition', value: String(++position)});
      }
      node.children?.forEach(visit);
    }
    visit(tree);
  };
}

/** Keep figure titles and keys in downloadable Markdown and search ingestion. */
function serializeDiagramFigures(content) {
  let position = 0;
  return content.replace(
    /^ {0,3}((`|~)\2{2,})[^\r\n]*\r?\n[\s\S]*?(?:^ {0,3}\1\2*[ \t]*(?=\r?$)|(?![\s\S]))|<DiagramFigure\s+\{\.\.\.(\{[\s\S]*?\})\}\s*>([\s\S]*?)<\/DiagramFigure>/gm,
    (match, fence, _marker, json, body) => {
      if (fence) return match;
      const {title, legend} = JSON.parse(json);
      if (typeof title !== 'string' || !title.trim()
        || !Array.isArray(legend) || !legend.length
        || new Set(legend.map(item => item.role)).size !== legend.length
        || legend.some(item => !Object.hasOwn(roles, item.role)
          || (item.label !== undefined && (typeof item.label !== 'string' || !item.label.trim())))) {
        throw new Error('DiagramFigure requires a title and unique valid legend roles');
      }
      const text = value => value.replace(/([\\`*_\[\]<>#])/g, '\\$1').replace(/\r?\n/g, ' ');
      const key = legend.map(({role, label}) => `- ${text(label || roles[role].label)}`).join('\n');
      const diagrams = body.trim().replace(/```mermaid\n([\s\S]*?)\n```/g,
        (_fence, source) => `\`\`\`mermaid\n${prepareMermaid(source).trimEnd()}\n\`\`\``);
      return `**Figure ${++position}. ${text(title)}**\n\n${diagrams}\n\n**Colour and icon key**\n\n${key}`;
    },
  );
}

module.exports = {numberDiagramFigures, serializeDiagramFigures};
