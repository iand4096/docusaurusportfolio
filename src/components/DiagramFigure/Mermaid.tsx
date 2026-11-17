import React, {useEffect, useRef, type CSSProperties, type ReactNode} from 'react';
import ErrorBoundary from '@docusaurus/ErrorBoundary';
import {ErrorBoundaryErrorMessageFallback} from '@docusaurus/theme-common';
import {MermaidContainerClassName, useMermaidRenderResult} from '@docusaurus/theme-mermaid/client';
import type {Props} from '@theme/Mermaid';
import {prepareMermaid} from './theme.cjs';

function Renderer({value}: Props): ReactNode {
  const result = useMermaidRenderResult({text: prepareMermaid(value)});
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current && result) result.bindFunctions?.(ref.current);
  }, [result]);

  if (!result) return null;
  // Keep at least 90% of Mermaid's natural text size. Narrow figures scroll
  // locally instead of squeezing wide graphs into unreadable thumbnails.
  const width = Number(result.svg.match(/<svg\b[^>]*\bviewBox="[^"\s]+\s+[^"\s]+\s+([\d.]+)/)?.[1]);
  const style = Number.isFinite(width) && width > 0
    ? {'--diagram-min-width': `${width * 0.9}px`, '--diagram-expanded-width': `${width * 1.25}px`} as CSSProperties : undefined;
  return <div ref={ref} className={MermaidContainerClassName} style={style}
    dangerouslySetInnerHTML={{__html: result.svg}} />;
}

export default function FigureMermaid(props: Props): ReactNode {
  return <ErrorBoundary fallback={params => <ErrorBoundaryErrorMessageFallback {...params} />}>
    <Renderer {...props} />
  </ErrorBoundary>;
}
