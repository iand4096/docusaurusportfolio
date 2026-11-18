import React, {useCallback, useEffect, useId, useRef, useState, type CSSProperties, type ReactNode} from 'react';
import {useHistory, useLocation} from '@docusaurus/router';
import Heading from '@theme/Heading';
import {DiagramDirectionContext, DiagramFigureContext, type DiagramDirection} from './context';
import {roles, type DiagramRole} from './theme.cjs';
import styles from './styles.module.css';

export type LegendItem = Readonly<{role: DiagramRole; label?: string}>;
export type DiagramFigureProps = Readonly<{
  number: number;
  title: string;
  shareId?: string;
  legend: readonly LegendItem[];
  children: ReactNode;
}>;

type DiagramPanel = {key: string; title: string; shareId?: string};

const fullScreenHint = 'Double-click the diagram to open or close full-screen.';

function isDiagramTarget(target: EventTarget | null): target is Element {
  return target instanceof Element && !!target.closest('svg') && !target.closest('a, button');
}

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
export default function DiagramFigure({number, title, shareId, legend, children}: DiagramFigureProps): ReactNode {
  const id = useId();
  const anchor = shareId ? `diagram-${shareId}` : undefined;
  const {pathname, search} = useLocation();
  const layoutKey = shareId ? `diagram-fullscreen-layout:${pathname.replace(/\/$/, '')}:${shareId}` : undefined;
  const history = useHistory();
  const opener = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const viewport = useRef<HTMLDivElement>(null);
  const panContent = useRef<HTMLDivElement>(null);
  const layoutSwitch = useRef<HTMLButtonElement>(null);
  const drag = useRef<{id: number; x: number; y: number} | null>(null);
  const [view, setView] = useState({zoom: 1, x: 0, y: 0});
  const [fitScale, setFitScale] = useState(1);
  const [dragging, setDragging] = useState(false);
  const canvas = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [panels, setPanels] = useState<DiagramPanel[]>([]);
  const [selectedPanel, setSelectedPanel] = useState<string>();
  const activePanel = panels.find(panel => panel.key === selectedPanel);
  const showingAllPanels = panels.length > 1 && !activePanel;
  const viewScale = fitScale * view.zoom;
  const zoomPercent = Math.round(view.zoom * 100);
  const [direction, setDirection] = useState<DiagramDirection>();
  const [authoredDirection, setAuthoredDirection] = useState<DiagramDirection>();
  const [savedDirection, setSavedDirection] = useState<DiagramDirection>();
  const currentDirection = direction ?? authoredDirection;
  const nextDirection = currentDirection === 'LR' ? 'TB' : 'LR';
  const defaultDirection = savedDirection ?? authoredDirection;
  const canSaveLayout = layoutKey && defaultDirection && currentDirection && currentDirection !== defaultDirection;
  const [reservedHeight, setReservedHeight] = useState<number>();
  const [viewerStatus, setViewerStatus] = useState('');
  const [manualLink, setManualLink] = useState('');
  const manualLinkInput = useRef<HTMLInputElement>(null);
  const copyAttempt = useRef(0);
  const caption = `Figure ${number}. ${title}`;

  const openViewer = useCallback((panel?: string, layout?: DiagramDirection) => {
    copyAttempt.current++;
    setReservedHeight(canvas.current?.getBoundingClientRect().height);
    setView({zoom: 1, x: 0, y: 0});
    setDragging(false);
    drag.current = null;
    let preferredLayout: DiagramDirection | undefined;
    if (layoutKey) {
      try {
        const savedLayout = window.localStorage.getItem(layoutKey);
        if (savedLayout === 'TB' || savedLayout === 'LR') preferredLayout = savedLayout;
      } catch {
        // Use the authored layout if browser storage is unavailable.
      }
    }
    setSavedDirection(preferredLayout);
    setDirection(layout ?? preferredLayout);
    setAuthoredDirection(undefined);
    setSelectedPanel(panel);
    setViewerStatus('');
    setManualLink('');
    setExpanded(true);
  }, [layoutKey]);

  useEffect(() => {
    const params = new URLSearchParams(search);
    if (!shareId || params.get('diagram') !== shareId) return;
    const layout = params.get('layout');
    if (!dialog.current?.open) opener.current?.focus({preventScroll: true});
    openViewer(params.get('panel') || undefined, layout === 'lr' ? 'LR' : layout === 'tb' ? 'TB' : undefined);
  }, [pathname, search, shareId, openViewer]);

  useEffect(() => {
    if (manualLink) manualLinkInput.current?.focus();
  }, [manualLink]);

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
      const options = panels.map((panel, index): DiagramPanel => {
        const shareId = panel.dataset.diagramPanelId;
        return {
          key: shareId || `panel:${index}`,
          title: panel.querySelector('h4')?.textContent?.replaceAll('\u200b', '').trim() || `Diagram ${index + 1}`,
          shareId,
        };
      });
      setPanels(previous => previous.length === options.length && previous.every((panel, index) =>
        panel.key === options[index].key && panel.title === options[index].title) ? previous : options);
      const selectedIndex = options.findIndex(panel => panel.key === selectedPanel);
      panels.forEach((panel, index) => {
        panel.hidden = selectedIndex >= 0 && selectedIndex !== index;
        const heading = panel.querySelector(':scope > h4');
        if (heading) observer.observe(heading);
      });
      const activeContent = selectedIndex < 0 ? content : panels[selectedIndex];
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

  function handleClose() {
    copyAttempt.current++;
    setExpanded(false);
    const params = new URLSearchParams(search);
    if (!shareId || params.get('diagram') !== shareId) return;
    for (const key of ['diagram', 'panel', 'layout']) params.delete(key);
    const remaining = params.toString();
    history.replace({pathname, search: remaining ? `?${remaining}` : '', hash: `#${anchor}`});
    opener.current?.closest('figure')?.scrollIntoView();
  }

  function saveDefaultLayout() {
    if (!layoutKey || !currentDirection) return;
    copyAttempt.current++;
    setManualLink('');
    try {
      window.localStorage.setItem(layoutKey, currentDirection);
      layoutSwitch.current?.focus();
      setSavedDirection(currentDirection);
      const label = currentDirection === 'LR' ? 'Left to right' : 'Top to bottom';
      setViewerStatus(`${label} saved as default.`);
    } catch {
      setViewerStatus('Could not save the layout preference in this browser.');
    }
  }

  async function copyShareLink() {
    if (!shareId || !anchor) return;
    const attempt = ++copyAttempt.current;
    const url = new URL(window.location.href);
    url.hash = anchor;
    url.searchParams.set('diagram', shareId);
    url.searchParams.delete('panel');
    url.searchParams.delete('layout');
    if (activePanel?.shareId) url.searchParams.set('panel', activePanel.shareId);
    if (currentDirection) url.searchParams.set('layout', currentDirection.toLowerCase());
    setViewerStatus('');
    setManualLink('');
    try {
      await navigator.clipboard.writeText(url.href);
      if (attempt === copyAttempt.current) setViewerStatus('Link copied');
    } catch {
      if (attempt !== copyAttempt.current) return;
      setManualLink(url.href);
      setViewerStatus('Select and copy the diagram link.');
    }
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
      <figcaption id={`${id}-caption`} className={anchor ? undefined : styles.title} title={fullScreenHint}>
        {anchor ? <Heading as="h4" id={anchor} className={styles.title}>{caption}</Heading> : caption}
      </figcaption>
      <div ref={canvas} className={styles.canvas} style={expanded ? {height: reservedHeight} : undefined}
        onDoubleClick={event => {
          if (!isDiagramTarget(event.target)) return;
          event.preventDefault();
          opener.current?.focus({preventScroll: true});
          const panel = event.target.closest<HTMLElement>('.diagram-panel');
          openViewer(panel?.dataset.diagramPanelId);
        }}>
        {!expanded && children}
      </div>
      <div className={styles.actions}>
        <button ref={opener} type="button" className={styles.expand} aria-haspopup="dialog"
          aria-controls={`${id}-dialog`} aria-label={`View full-screen: ${caption}`}
          title={fullScreenHint}
          onClick={() => openViewer()}>
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
        onClose={handleClose}>
        <header className={styles.toolbar}>
          <h2 id={`${id}-expanded-caption`} className={styles.title} title={fullScreenHint}>{caption}</h2>
          <div className={styles.headerActions}>
            {shareId && <button type="button" className={styles.shareButton}
              aria-label="Copy diagram link" title="Copy diagram link" onClick={copyShareLink}>
              <i className="fa-solid fa-link" aria-hidden="true" />
            </button>}
            <button type="button" className={styles.closeButton} autoFocus
              aria-label="Close" title="Close (Esc)" aria-keyshortcuts="Escape" onClick={closeViewer}>
              <i className="fa-solid fa-xmark" aria-hidden="true" /> <span>Close</span>
            </button>
          </div>
        </header>
        {shareId && <p className={styles.viewerStatus} role="status">{viewerStatus}</p>}
        {manualLink && <input ref={manualLinkInput} className={styles.shareLink} type="text"
          aria-label="Diagram link" value={manualLink} readOnly onFocus={event => event.target.select()} />}
        <div className={styles.controlBar}>
          {expanded && panels.length > 1 && <div className={styles.panelLinks} role="group" aria-label="Diagrams in this figure">
            {[undefined, ...panels].map(panel => (
              <button key={panel?.key ?? 'all'} type="button"
                aria-pressed={activePanel === panel}
                onClick={() => {
                  setSelectedPanel(panel?.key);
                  setView({zoom: 1, x: 0, y: 0});
                }}>
                {panel?.title ?? 'All diagrams'}
              </button>
            ))}
          </div>}
          <div className={styles.viewControls}>
            {currentDirection && <div className={`${styles.controlGroup} ${styles.layoutControls}`}
              role="group" aria-label="Diagram layout">
              <span aria-hidden="true">Switch layout</span>
              <button ref={layoutSwitch} type="button" className={styles.layoutButton}
                title={nextDirection === 'LR' ? 'Switch to left-to-right layout' : 'Switch to top-to-bottom layout'}
                onClick={() => {
                  setDirection(nextDirection);
                  setView({zoom: 1, x: 0, y: 0});
                }}>
                <i className={`fa-solid ${nextDirection === 'LR' ? 'fa-arrows-left-right' : 'fa-arrows-up-down'}`}
                  aria-hidden="true" />
                {nextDirection === 'LR' ? 'Left to right' : 'Top to bottom'}
              </button>
              {canSaveLayout && <button type="button" className={styles.layoutButton}
                title="Use this layout when opening this figure full-screen."
                onClick={saveDefaultLayout}>Set as default</button>}
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
            onDoubleClick={event => {
              // Pointer capture for panning can retarget the click to the viewport.
              const target = event.target === event.currentTarget
                ? document.elementFromPoint(event.clientX, event.clientY) : event.target;
              if (isDiagramTarget(target)) closeViewer();
            }}
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
              data-single-panel={!!activePanel || undefined}
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
