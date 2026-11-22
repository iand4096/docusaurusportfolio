import React, {useContext, useEffect, useRef, type CSSProperties, type ReactNode} from 'react';
import ErrorBoundary from '@docusaurus/ErrorBoundary';
import {ErrorBoundaryErrorMessageFallback} from '@docusaurus/theme-common';
import {MermaidContainerClassName, useMermaidRenderResult} from '@docusaurus/theme-mermaid/client';
import type {Props} from '@theme/Mermaid';
import {DiagramDirectionContext} from './context';
import {flowchartDirection, flowchartWithDirection, prepareMermaid} from './theme.cjs';

function Renderer({value}: Props): ReactNode {
  const result = useMermaidRenderResult({text: prepareMermaid(value)});
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current && result) result.bindFunctions?.(ref.current);
  }, [result]);

  if (!result) return null;
  // Keep at least 90% of Mermaid's natural text size. Narrow figures scroll
  // locally instead of squeezing wide graphs into unreadable thumbnails.
  const viewBox = result.svg.match(/<svg\b[^>]*\bviewBox="([^"]+)"/)?.[1];
  const [, , width, height] = viewBox?.trim().split(/[\s,]+/).map(Number) ?? [];
  const style = width > 0 && height > 0 ? {
    '--diagram-min-width': `${width * 0.9}px`,
    '--diagram-aspect-ratio': width / height,
  } as CSSProperties : undefined;
  const subgraphIds = Array.from(value.matchAll(/^[ \t]*subgraph[ \t]+([\w-]+)(?=[ \t]*(?:\[|\r?$))/gm),
    match => match[1]).join(' ');
  return <div ref={ref} className={MermaidContainerClassName} style={style}
    data-diagram-subgraph-ids={subgraphIds || undefined}
    data-diagram-subgraph-direction={flowchartDirection(value)}
    dangerouslySetInnerHTML={{__html: result.svg}} />;
}

export default function FigureMermaid(props: Props): ReactNode {
  const direction = useContext(DiagramDirectionContext);
  const authoredDirection = direction === null ? undefined : flowchartDirection(props.value);
  const orientedSource = direction && flowchartWithDirection(props.value, direction);
  return <>
    {authoredDirection && <span hidden data-diagram-authored-direction={authoredDirection}
      data-diagram-rendered-direction={direction ?? authoredDirection} />}
    <ErrorBoundary key={orientedSource ? direction : undefined}
      fallback={params => <ErrorBoundaryErrorMessageFallback {...params} />}>
      <Renderer {...props} value={orientedSource ?? props.value} />
    </ErrorBoundary>
  </>;
}
