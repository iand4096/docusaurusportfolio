import React from 'react';
import MermaidZoom from '@site/src/components/MermaidZoom';

export default function Root({children}) {
  return <><MermaidZoom />{children}</>;
}
