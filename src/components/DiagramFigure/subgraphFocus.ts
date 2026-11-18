export type SubgraphOption = {id: string; panel?: string; label: string};
export type SubgraphFit = {
  scale: number; x: number; y: number; width: number; height: number; limited: boolean;
  offsetX: number; offsetY: number;
};

const maxLabelSize = 24;

export function subgraphKey({id, panel}: SubgraphOption): string {
  return JSON.stringify([panel, id]);
}

export function findSubgraphs(content: HTMLElement) {
  const panels = Array.from(content.querySelectorAll<HTMLElement>('.diagram-columns > .diagram-panel'));
  const renderers = content.querySelectorAll<HTMLElement>('[data-diagram-subgraph-ids]');
  return Array.from(renderers).flatMap(renderer => {
    if (renderer.closest('[hidden]')) return [];
    const ids = (renderer.dataset.diagramSubgraphIds?.split(' ') ?? []).sort((a, b) => b.length - a.length);
    const panel = renderer.closest<HTMLElement>('.diagram-panel');
    const panelKey = panel ? panel.dataset.diagramPanelId || `panel:${panels.indexOf(panel)}` : undefined;
    const horizontal = renderer.dataset.diagramSubgraphDirection === 'LR';
    const targets = Array.from(renderer.querySelectorAll<SVGGElement>('svg g.cluster[id]')).flatMap(element => {
      // Mermaid can prefix rendered cluster IDs. Match the longest authored suffix.
      const id = ids.find(candidate => element.id === candidate)
        ?? ids.find(candidate => element.id.endsWith(`-${candidate}`));
      if (!id) return [];
      const {left, top} = element.getBoundingClientRect();
      return [{id, element, panel: panelKey, left, top,
        label: element.querySelector('.cluster-label')?.textContent?.replace(/\s+/g, ' ').trim() || id}];
    });
    return targets.sort((a, b) => horizontal
      ? a.left - b.left || a.top - b.top
      : a.top - b.top || a.left - b.left);
  });
}

export function fitSubgraph(frame: HTMLElement, content: HTMLElement, element: SVGGElement): SubgraphFit | undefined {
  const scale = Number(content.style.getPropertyValue('--diagram-view-scale'));
  const {clientWidth: width, clientHeight: height} = frame;
  const area = content.getBoundingClientRect();
  const target = element.getBoundingClientRect();
  if (!(scale > 0 && width > 0 && height > 0 && target.width > 0 && target.height > 0)) return undefined;

  const padding = Math.min(16, width / 10, height / 10);
  const fullFit = Math.min((width - 2 * padding) / target.width, (height - 2 * padding) / target.height);
  let largestLabel = 0;
  const svg = element.ownerSVGElement;
  for (const label of svg?.querySelectorAll('.nodeLabel') ?? []) {
    const rect = label.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;
    if (!rect.width || !rect.height || x < target.left || x > target.right || y < target.top || y > target.bottom) continue;
    // HTML labels sit in a foreignObject. Its matrix includes the SVG and viewer scales.
    const svgLabel = label.closest('foreignObject') ?? label;
    const matrix = svgLabel instanceof SVGGraphicsElement ? svgLabel.getScreenCTM() : svg?.getScreenCTM();
    const size = parseFloat(getComputedStyle(label).fontSize);
    if (matrix && Number.isFinite(size)) largestLabel = Math.max(largestLabel, size * Math.hypot(matrix.a, matrix.b));
  }
  const labelFit = largestLabel > 0 ? maxLabelSize / largestLabel : fullFit;
  const ratio = Math.min(fullFit, labelFit);
  const horizontal = element.closest<HTMLElement>('[data-diagram-subgraph-direction]')
    ?.dataset.diagramSubgraphDirection === 'LR';
  const graph = svg?.querySelector('g.root')?.getBoundingClientRect();
  let shift = 0;
  if (graph) {
    const margin = ((horizontal ? width : height) - (horizontal ? target.width : target.height) * ratio) / 2;
    const leadingContext = (horizontal ? target.left - graph.left : target.top - graph.top) * ratio;
    const trailingContext = (horizontal ? graph.right - target.right : graph.bottom - target.bottom) * ratio;
    // Use only blank space at the start, and only as far as it reveals more of the graph.
    const availableShift = Math.min(margin - Math.max(0, leadingContext) - padding, trailingContext - margin);
    if (availableShift >= 12) shift = -availableShift;
  }
  return {
    scale: scale * ratio,
    x: (target.left + target.width / 2 - area.left - area.width / 2) / scale,
    y: (target.top + target.height / 2 - area.top - area.height / 2) / scale,
    width: target.width / scale,
    height: target.height / scale,
    limited: labelFit < fullFit,
    offsetX: horizontal ? shift : 0,
    offsetY: horizontal ? 0 : shift,
  };
}
