export type SubgraphOption = {id: string; panel?: string; label: string};
export type SubgraphFit = {
  scale: number; x: number; y: number; width: number; height: number; limited: boolean;
  offsetX: number; offsetY: number; frameWidth: number; frameHeight: number;
};
export type NoteConnector = {left: number; top: number; length: number; vertical: boolean};
type OutlinePoint = {x: number; y: number};
type NodeOutline = OutlinePoint[][];

function findOutlineEdge(outline: NodeOutline, cross: number, from: number, vertical: boolean) {
  let edge: number | undefined;
  for (const points of outline) {
    for (let index = 1; index < points.length; index++) {
      const a = points[index - 1];
      const b = points[index];
      const start = vertical ? a.x : a.y;
      const end = vertical ? b.x : b.y;
      if (start === end || cross < Math.min(start, end) || cross > Math.max(start, end)) continue;
      const fraction = (cross - start) / (end - start);
      const along = vertical ? a.y + (b.y - a.y) * fraction : a.x + (b.x - a.x) * fraction;
      if (edge === undefined || Math.abs(along - from) < Math.abs(edge - from)) edge = along;
    }
  }
  return edge;
}

export function placeSubgraphNote(
  frame: DOMRect, target: DOMRect, note: DOMRect, obstacles: DOMRect[],
  nodeDirection?: 'LR' | 'TB', outline?: NodeOutline, zoom = 1,
) {
  const inset = 12;
  const clampTop = (top: number) => Math.max(frame.top + inset, Math.min(top, frame.bottom - note.height - inset));
  const clampLeft = (left: number) => Math.max(frame.left + inset, Math.min(left, frame.right - note.width - inset));
  const sides = nodeDirection === 'LR'
    ? ['above', 'below', 'right', 'left'] as const
    : ['right', 'left', 'below', 'above'] as const;
  const gaps = (nodeDirection ? [24, 40, 56, 80] : [24]).map(gap => gap * zoom);
  const candidates = sides.flatMap(side => {
    const vertical = side === 'above' || side === 'below';
    const alignments = vertical
      ? [target.left, (target.left + target.right - note.width) / 2, target.right - note.width].map(clampLeft)
      : [target.top, (target.top + target.bottom - note.height) / 2, target.bottom - note.height].map(clampTop);
    const positions = nodeDirection ? [...new Set(alignments)] : alignments.slice(0, 1);
    return gaps.flatMap(gap => positions.map(position => ({
      side, vertical,
      left: vertical ? position : side === 'right' ? target.right + gap : target.left - note.width - gap,
      top: vertical ? side === 'below' ? target.bottom + gap : target.top - note.height - gap : position,
    })));
  });
  const blocked = (left: number, top: number, right: number, bottom: number, padding = 4) =>
    obstacles.some(box => left < box.right + padding && right > box.left - padding
      && top < box.bottom + padding && bottom > box.top - padding);
  for (const {left, top, side, vertical} of candidates) {
    const right = left + note.width;
    const bottom = top + note.height;
    if (left < frame.left + inset || right > frame.right - inset
      || top < frame.top + inset || bottom > frame.bottom - inset || blocked(left, top, right, bottom)) continue;

    const start = vertical ? Math.max(left, target.left) : Math.max(top, target.top);
    const end = vertical ? Math.min(right, target.right) : Math.min(bottom, target.bottom);
    if (start >= end) continue;
    const mid = (start + end) / 2;
    const noteEdge = side === 'left' ? right : side === 'right' ? left : side === 'above' ? bottom : top;
    const boxEdge = side === 'left' ? target.left : side === 'right' ? target.right
      : side === 'above' ? target.top : target.bottom;
    const targetEdge = outline?.length ? findOutlineEdge(outline, mid, noteEdge, vertical) : boxEdge;
    if (targetEdge === undefined) continue;
    const lineStart = Math.min(noteEdge, targetEdge);
    const length = Math.abs(noteEdge - targetEdge);
    const connector: NoteConnector = {
      left: vertical ? mid : lineStart,
      top: vertical ? lineStart : mid,
      length,
      vertical,
    };
    const {left: x, top: y} = connector;
    // A partially visible target must still have an on-canvas attachment point.
    if (x < frame.left || y < frame.top || x + (vertical ? 0 : length) > frame.right
      || y + (vertical ? length : 0) > frame.bottom) continue;
    // Ignore the two ends of the leader where it deliberately touches the boxes.
    const endClearance = 5 * zoom;
    const leaderBlocked = vertical
      ? blocked(x, y + endClearance, x, y + length - endClearance, 4 * zoom)
      : blocked(x + endClearance, y, x + length - endClearance, y, 4 * zoom);
    if (!leaderBlocked) return {left, top, connector};
  }
  return undefined;
}

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
    frameWidth: width,
    frameHeight: height,
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

export type DiagramNotes = Readonly<Record<string, string | Readonly<Record<string, string>>>>;
export type NoteTarget = {element: SVGGElement; key: string; title: string; text: string; subgraph?: true};

export function diagramNote(notes: DiagramNotes | undefined, panel: string | undefined, id: string) {
  const entries = panel ? notes?.[panel] : notes;
  const text = typeof entries === 'object' ? entries[id] : undefined;
  return typeof text === 'string' && text.trim() ? text : undefined;
}

export function nodeOutline(element: SVGGElement): NodeOutline {
  const shape = element.querySelector('.label-container');
  const geometry = shape instanceof SVGGeometryElement ? [shape]
    : Array.from(shape?.querySelectorAll('path, polygon, rect, circle, ellipse') ?? [])
      .filter((part): part is SVGGeometryElement => part instanceof SVGGeometryElement && !part.closest('.label'));
  return geometry.flatMap(part => {
    const matrix = part.getScreenCTM();
    if (!matrix) return [];
    if (part instanceof SVGPolygonElement && part.points.length) {
      const points = Array.from(part.points, point => point.matrixTransform(matrix));
      return [[...points, points[0]]];
    }
    const length = part.getTotalLength();
    if (!length) return [];
    // Sample in SVG units, then transform to the panned and zoomed viewport.
    const segments = Math.min(96, Math.max(16, Math.ceil(length / 4)));
    return [Array.from({length: segments + 1}, (_, index) =>
      part.getPointAtLength(length * index / segments).matrixTransform(matrix))];
  });
}

export function noteMarkerAnchor({element, subgraph}: NoteTarget, frame: HTMLElement, zoom: number) {
  const bounds = frame.getBoundingClientRect();
  const originX = bounds.left + frame.clientLeft;
  const originY = bounds.top + frame.clientTop;
  const node = element.getBoundingClientRect();
  if (node.right <= bounds.left || node.left >= bounds.right
    || node.bottom <= bounds.top || node.top >= bounds.bottom) return;

  const radius = 16 * zoom;
  const fits = (left: number, top: number) => left >= radius && left <= frame.clientWidth - radius
    && top >= radius && top <= frame.clientHeight - radius;
  if (subgraph) {
    const left = node.left - originX;
    const right = node.right - originX;
    const top = node.top - originY;
    const bottom = node.bottom - originY;
    const edgeX = Math.min(right, frame.clientWidth - radius);
    const edgeY = Math.max(top, radius);
    const corners = [[right, top], [left, top], [right, bottom], [left, bottom]];
    const edgePoints = [[edgeX, top], [right, edgeY], [left, edgeY], [edgeX, bottom]];
    for (const [x, y] of [...corners, ...edgePoints]) {
      if (x >= left && x <= right && y >= top && y <= bottom && fits(x, y)) return {left: x, top: y};
    }
    return;
  }

  const outline = element.querySelector('rect.label-container') ? [] : nodeOutline(element).flat();
  if (!outline.length) {
    const left = node.right - originX;
    const top = node.top - originY;
    if (left >= 0 && left < frame.clientWidth && top >= 0 && top < frame.clientHeight) return {left, top};
    return;
  }

  // Keep the whole marker visible while its centre touches the outline.
  const directions = [[0.8, -0.6], [0, -1], [-0.8, -0.6], [1, 0], [-1, 0], [0.8, 0.6], [-0.8, 0.6], [0, 1]];
  for (const [x, y] of directions) {
    const edge = outline.reduce((best, point) => (
      point.x * x + point.y * y > best.x * x + best.y * y ? point : best
    ));
    const left = edge.x - originX;
    const top = edge.y - originY;
    if (fits(left, top)) return {left, top};
  }
}

export function findNodeNotes(content: HTMLElement, notes: DiagramNotes): NoteTarget[] {
  const panels = Array.from(content.querySelectorAll<HTMLElement>('.diagram-columns > .diagram-panel'));
  return Array.from(content.querySelectorAll<SVGGElement>('svg g.node[id]')).flatMap(element => {
    if (element.closest('[hidden], .cluster')) return [];
    const svg = element.ownerSVGElement;
    if (!svg?.closest('[data-diagram-flowchart]')) return [];
    // Some Mermaid layouts only expose the authored ID inside the generated DOM ID.
    const id = element.dataset.id ?? element.id.match(/(?:^|-)flowchart-(.+)-\d+$/)?.[1];
    if (!id) return [];
    const panel = element.closest<HTMLElement>('.diagram-panel');
    const panelId = panel ? panel.dataset.diagramPanelId || `panel:${panels.indexOf(panel)}` : undefined;
    const text = diagramNote(notes, panelId, id);
    if (!text) return [];

    // Mermaid can render members and their cluster box in separate SVG groups.
    const box = element.getBoundingClientRect();
    const x = box.left + box.width / 2;
    const y = box.top + box.height / 2;
    const insideCluster = Array.from(svg.querySelectorAll('g.cluster')).some(cluster => {
      const bounds = cluster.getBoundingClientRect();
      return x > bounds.left && x < bounds.right && y > bounds.top && y < bounds.bottom;
    });
    if (insideCluster) return [];

    const label = element.querySelector('.nodeLabel, .label')?.textContent?.replace(/\s+/g, ' ').trim() || id;
    return [{element, key: JSON.stringify(['node', panelId, id]), title: `About ${label}`, text}];
  });
}
