import React, {useContext, type ReactNode} from 'react';
import Mermaid from '@theme-original/Mermaid';
import type {Props} from '@theme/Mermaid';
import {DiagramFigureContext} from '@site/src/components/DiagramFigure/context';
import FigureMermaid from '@site/src/components/DiagramFigure/Mermaid';

export default function MermaidWrapper({value, ...props}: Props): ReactNode {
  const isFigure = useContext(DiagramFigureContext);
  return isFigure ? <FigureMermaid {...props} value={value} /> : <Mermaid {...props} value={value} />;
}
