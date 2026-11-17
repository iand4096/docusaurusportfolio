import React, {useEffect, useId, useRef, useState, type ReactNode} from 'react';
import {DiagramFigureContext} from './context';
import {roles, type DiagramRole} from './theme.cjs';
import styles from './styles.module.css';

export type LegendItem = Readonly<{role: DiagramRole; label?: string}>;
export type DiagramFigureProps = Readonly<{
  number: number;
  title: string;
  legend: readonly LegendItem[];
  children: ReactNode;
}>;

function Legend({items}: {items: readonly LegendItem[]}): ReactNode {
  return <ul className={styles.legend} aria-label="Colour and icon key">
    {items.map(({role, label}) => {
      const {fill, stroke, icon, label: defaultLabel} = roles[role];
      return <li key={role}>
        <span className={styles.swatch} style={{backgroundColor: fill, borderColor: stroke}} aria-hidden="true">
          {icon && <i className={`fa-solid fa-${icon}`} />}
        </span>
        <span>{label || defaultLabel}</span>
      </li>;
    })}
  </ul>;
}

/** One titled figure may contain a single Mermaid diagram or several panels. */
export default function DiagramFigure({number, title, legend, children}: DiagramFigureProps): ReactNode {
  const id = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const viewport = useRef<HTMLDivElement>(null);
  const drag = useRef<{id: number; x: number; y: number} | null>(null);
  const [view, setView] = useState({zoom: 1, x: 0, y: 0});
  const [dragging, setDragging] = useState(false);
  const canvas = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [reservedHeight, setReservedHeight] = useState<number>();
  const caption = `Figure ${number}. ${title}`;

  useEffect(() => {
    if (expanded && !dialog.current?.open) dialog.current?.showModal();
  }, [expanded]);

  function zoomBy(factor: number) {
    const element = viewport.current;
    if (!element) return;
    const cx = element.clientWidth / 2;
    const cy = element.clientHeight / 2;
    setView(previous => {
      const zoom = Math.min(4, Math.max(0.25, previous.zoom * factor));
      const ratio = zoom / previous.zoom;
      return {zoom, x: cx - (cx - previous.x) * ratio, y: cy - (cy - previous.y) * ratio};
    });
  }

  useEffect(() => {
    if (!expanded) return;
    const element = viewport.current;
    if (!element) return;
    const wheel = (event: WheelEvent) => {
      event.preventDefault();
      const pixels = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? element.clientHeight : 1);
      zoomBy(Math.exp(-Math.max(-100, Math.min(100, pixels)) * 0.002));
    };
    element.addEventListener('wheel', wheel, {passive: false});
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      element.removeEventListener('wheel', wheel);
      document.body.style.overflow = overflow;
    };
  }, [expanded]);

  return <DiagramFigureContext.Provider value={true}>
    <figure className={styles.figure} aria-labelledby={`${id}-caption`}>
      <figcaption id={`${id}-caption`} className={styles.title}>{caption}</figcaption>
      <div ref={canvas} className={styles.canvas} style={expanded ? {height: reservedHeight} : undefined}>
        {!expanded && children}
      </div>
      <div className={styles.actions}>
        <button type="button" className={styles.expand} aria-haspopup="dialog"
          aria-controls={`${id}-dialog`} aria-label={`View full-screen: ${caption}`}
          onClick={() => {
            setReservedHeight(canvas.current?.getBoundingClientRect().height);
            setView({zoom: 1, x: 0, y: 0});
            setDragging(false);
            drag.current = null;
            setExpanded(true);
          }}>
          <i className="fa-solid fa-expand" aria-hidden="true" /> View full-screen
        </button>
      </div>
      <Legend items={legend} />
      <dialog ref={dialog} id={`${id}-dialog`} className={styles.dialog}
        aria-labelledby={`${id}-expanded-caption`} onClose={() => setExpanded(false)}>
        <div className={styles.toolbar}>
          <h2 id={`${id}-expanded-caption`} className={styles.title}>{caption}</h2>
          <div className={styles.controls} role="group" aria-label="Diagram zoom controls">
            <button type="button" className={styles.zoomButton} aria-label="Zoom out"
              title="Zoom out (or scroll the mouse wheel down over the diagram)"
              disabled={view.zoom <= 0.25} onClick={() => zoomBy(1 / 1.2)}>
              <i className="fa-solid fa-minus" aria-hidden="true" />
            </button>
            <output className={styles.zoomLevel} aria-label="Zoom level">{Math.round(view.zoom * 100)}%</output>
            <button type="button" className={styles.zoomButton} aria-label="Zoom in"
              title="Zoom in (or scroll the mouse wheel up over the diagram)"
              disabled={view.zoom >= 4} onClick={() => zoomBy(1.2)}>
              <i className="fa-solid fa-plus" aria-hidden="true" />
            </button>
          </div>
          <button type="button" className="button button--secondary button--sm" autoFocus
            onClick={() => dialog.current?.close()}>Close</button>
        </div>
        {expanded && <div className={styles.expanded}>
          <div ref={viewport} className={styles.viewport} data-dragging={dragging || undefined}
            role="region" tabIndex={0} aria-label="Diagram viewport: use the mouse wheel to zoom, drag to pan, or use arrow keys to pan"
            onPointerDown={event => {
              if (event.button !== 0 || drag.current || (event.target as Element).closest('a, button')) return;
              event.preventDefault();
              event.currentTarget.focus({preventScroll: true});
              event.currentTarget.setPointerCapture(event.pointerId);
              drag.current = {id: event.pointerId, x: event.clientX, y: event.clientY};
              setDragging(true);
            }}
            onPointerMove={event => {
              const current = drag.current;
              if (!current || current.id !== event.pointerId) return;
              const dx = event.clientX - current.x;
              const dy = event.clientY - current.y;
              current.x = event.clientX;
              current.y = event.clientY;
              setView(previous => ({...previous, x: previous.x + dx, y: previous.y + dy}));
            }}
            onPointerUp={event => {
              if (drag.current?.id !== event.pointerId) return;
              event.currentTarget.releasePointerCapture(event.pointerId);
              drag.current = null;
              setDragging(false);
            }}
            onPointerCancel={() => {drag.current = null; setDragging(false);}}
            onLostPointerCapture={() => {drag.current = null; setDragging(false);}}
            onKeyDown={event => {
              const offsets: Record<string, [number, number]> = {
                ArrowLeft: [40, 0], ArrowRight: [-40, 0], ArrowUp: [0, 40], ArrowDown: [0, -40],
              };
              const offset = offsets[event.key];
              if (!offset) return;
              event.preventDefault();
              setView(previous => ({...previous, x: previous.x + offset[0], y: previous.y + offset[1]}));
            }}>
            <div className={`${styles.canvas} ${styles.panContent}`}
              style={{transform: `translate(${view.x}px, ${view.y}px) scale(${view.zoom})`}}>{children}</div>
          </div>
          <Legend items={legend} />
        </div>}
      </dialog>
    </figure>
  </DiagramFigureContext.Provider>;
}
