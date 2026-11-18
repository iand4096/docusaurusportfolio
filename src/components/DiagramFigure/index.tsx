import React, {useEffect, useId, useRef, useState, type CSSProperties, type ReactNode} from 'react';
import {DiagramDirectionContext, DiagramFigureContext, type DiagramDirection} from './context';
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
      return <li key={role} title={`Category: ${defaultLabel}`}>
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
  const panContent = useRef<HTMLDivElement>(null);
  const drag = useRef<{id: number; x: number; y: number} | null>(null);
  const [view, setView] = useState({zoom: 1, x: 0, y: 0});
  const [fitScale, setFitScale] = useState(1);
  const [dragging, setDragging] = useState(false);
  const canvas = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [panelTitles, setPanelTitles] = useState<string[]>([]);
  const [selectedPanel, setSelectedPanel] = useState<number>();
  const showingAllPanels = panelTitles.length > 1 && selectedPanel === undefined;
  const viewScale = fitScale * view.zoom;
  const zoomPercent = Math.round(view.zoom * 100);
  const [direction, setDirection] = useState<DiagramDirection>();
  const [authoredDirection, setAuthoredDirection] = useState<DiagramDirection>();
  const currentDirection = direction ?? authoredDirection;
  const nextDirection = currentDirection === 'LR' ? 'TB' : 'LR';
  const [reservedHeight, setReservedHeight] = useState<number>();
  const caption = `Figure ${number}. ${title}`;

  useEffect(() => {
    if (expanded && !dialog.current?.open) dialog.current?.showModal();
  }, [expanded]);

  useEffect(() => {
    const frame = viewport.current;
    const content = panContent.current;
    if (!expanded || !frame || !content) return;
    const fit = () => {
      const {offsetWidth: width, offsetHeight: height} = content;
      if (width && height && frame.clientWidth && frame.clientHeight) {
        setFitScale(Math.min(frame.clientWidth / width, frame.clientHeight / height));
      }
    };
    // Mermaid renders asynchronously. Measure the new diagram once its layout is ready.
    const observer = new ResizeObserver(entries => {
      for (const {target} of entries) {
        if (target instanceof HTMLElement && target.matches('.diagram-panel > h4')) {
          target.parentElement?.style.setProperty('--diagram-heading-height', `${target.offsetHeight}px`);
        }
      }
      fit();
    });
    observer.observe(frame);
    observer.observe(content);
    fit();
    const readPanels = () => {
      const panels = Array.from(content.querySelectorAll<HTMLElement>('.diagram-columns > .diagram-panel'));
      const titles = panels.map((panel, index) =>
        panel.querySelector('h4')?.textContent?.replaceAll('\u200b', '').trim() || `Diagram ${index + 1}`);
      setPanelTitles(previous => previous.length === titles.length
        && previous.every((title, index) => title === titles[index]) ? previous : titles);
      panels.forEach((panel, index) => {
        panel.hidden = selectedPanel !== undefined && selectedPanel !== index;
        const heading = panel.querySelector(':scope > h4');
        if (heading) observer.observe(heading);
      });
      const activeContent = selectedPanel === undefined ? content : panels[selectedPanel];
      const marker = activeContent?.querySelector<HTMLElement>('[data-diagram-authored-direction]');
      const authored = marker?.dataset.diagramAuthoredDirection;
      setAuthoredDirection(authored === 'LR' || authored === 'TB' ? authored : undefined);
      fit();
    };
    const diagrams = new MutationObserver(readPanels);
    diagrams.observe(content, {childList: true, subtree: true});
    readPanels();
    return () => {
      observer.disconnect();
      diagrams.disconnect();
    };
  }, [expanded, selectedPanel]);

  function zoomBy(factor: number) {
    setView(previous => {
      const zoom = Math.min(4, Math.max(0.25, previous.zoom * factor));
      const ratio = zoom / previous.zoom;
      return {zoom, x: previous.x * ratio, y: previous.y * ratio};
    });
  }

  function closeViewer() {
    dialog.current?.close();
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
            setDirection(undefined);
            setAuthoredDirection(undefined);
            setSelectedPanel(undefined);
            setExpanded(true);
          }}>
          <i className="fa-solid fa-expand" aria-hidden="true" /> View full-screen
        </button>
      </div>
      <Legend items={legend} />
      <dialog ref={dialog} id={`${id}-dialog`} className={styles.dialog}
        aria-labelledby={`${id}-expanded-caption`}
        onCancel={event => {
          event.preventDefault();
          closeViewer();
        }}
        onClose={() => setExpanded(false)}>
        <header className={styles.toolbar}>
          <h2 id={`${id}-expanded-caption`} className={styles.title}>{caption}</h2>
          <button type="button" className={styles.closeButton} autoFocus
            aria-label="Close" title="Close (Esc)" aria-keyshortcuts="Escape" onClick={closeViewer}>
            <i className="fa-solid fa-xmark" aria-hidden="true" /> <span>Close</span>
          </button>
        </header>
        <div className={styles.controlBar}>
          {expanded && panelTitles.length > 1 && <div className={styles.panelLinks} role="group" aria-label="Diagrams in this figure">
            {[undefined, ...panelTitles.map((_, index) => index)].map(index => (
              <button key={index ?? 'all'} type="button"
                aria-pressed={selectedPanel === index}
                onClick={() => {
                  setSelectedPanel(index);
                  setView({zoom: 1, x: 0, y: 0});
                }}>
                {index === undefined ? 'All diagrams' : panelTitles[index]}
              </button>
            ))}
          </div>}
          <div className={styles.viewControls}>
            {currentDirection && <div className={styles.controlGroup} role="group" aria-label="Diagram layout">
              <span aria-hidden="true">Layout</span>
              <button type="button" className={styles.layoutButton}
                onClick={() => {
                  setDirection(nextDirection);
                  setView({zoom: 1, x: 0, y: 0});
                }}>
                <i className={`fa-solid ${nextDirection === 'LR' ? 'fa-arrows-left-right' : 'fa-arrows-up-down'}`}
                  aria-hidden="true" />
                {nextDirection === 'LR' ? 'Left to right' : 'Top to bottom'}
              </button>
            </div>}
            <div className={styles.controlGroup} role="group" aria-label="Diagram zoom controls">
              <span aria-hidden="true">Zoom</span>
              <div className={styles.controls}>
                <button type="button" className={styles.zoomButton} aria-label="Zoom out"
                  title="Zoom out (or scroll the mouse wheel down over the diagram)"
                  disabled={view.zoom <= 0.25} onClick={() => zoomBy(1 / 1.2)}>
                  <i className="fa-solid fa-minus" aria-hidden="true" />
                </button>
                <button type="button" className={`${styles.zoomButton} ${styles.zoomLevel}`}
                  aria-label="Reset zoom and fit diagram" title="Reset zoom and fit diagram"
                  aria-description={`Current zoom: ${zoomPercent}%`}
                  onClick={() => setView({zoom: 1, x: 0, y: 0})}>
                  {zoomPercent}%
                </button>
                <button type="button" className={styles.zoomButton} aria-label="Zoom in"
                  title="Zoom in (or scroll the mouse wheel up over the diagram)"
                  disabled={view.zoom >= 4} onClick={() => zoomBy(1.2)}>
                  <i className="fa-solid fa-plus" aria-hidden="true" />
                </button>
              </div>
            </div>
          </div>
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
            <div ref={panContent} className={`${styles.canvas} ${styles.panContent}`}
              data-all-panels={showingAllPanels || undefined}
              data-single-panel={selectedPanel !== undefined || undefined}
              style={{
                '--diagram-view-scale': viewScale,
                transform: `translate(${view.x}px, ${view.y}px) scale(${viewScale}) translate(-50%, -50%)`,
              } as CSSProperties}>
              <DiagramDirectionContext.Provider value={direction}>{children}</DiagramDirectionContext.Provider>
            </div>
          </div>
          <Legend items={legend} />
        </div>}
      </dialog>
    </figure>
  </DiagramFigureContext.Provider>;
}
