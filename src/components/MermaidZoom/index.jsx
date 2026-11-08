import React, {useEffect, useRef} from 'react';

/** Add an accessible enlargement action to already-rendered Mermaid SVGs. */
export default function MermaidZoom() {
  const dialogRef = useRef(null);
  const contentRef = useRef(null);

  useEffect(() => {
    let timer;
    const enhance = () => {
      document.querySelectorAll('.theme-doc-markdown .mermaid').forEach((diagram) => {
        const svg = diagram.querySelector('svg');
        if (!svg || diagram.nextElementSibling?.matches('.mermaid-expand-button')) {
          return;
        }
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'mermaid-expand-button';
        button.textContent = 'Enlarge diagram';
        button.setAttribute('aria-label', 'Enlarge architecture diagram');
        button.addEventListener('click', () => {
          const source = diagram.querySelector('svg');
          if (!source || !contentRef.current || !dialogRef.current) return;
          contentRef.current.replaceChildren(source.cloneNode(true));
          dialogRef.current.showModal();
        });
        diagram.insertAdjacentElement('afterend', button);
      });
    };
    const observer = new MutationObserver(() => {
      window.clearTimeout(timer);
      timer = window.setTimeout(enhance, 120);
    });
    enhance();
    observer.observe(document.body, {childList: true, subtree: true});
    return () => {
      window.clearTimeout(timer);
      observer.disconnect();
    };
  }, []);

  return (
    <dialog ref={dialogRef} className="mermaid-lightbox" aria-label="Expanded diagram">
      <div className="mermaid-lightbox__toolbar">
        <span>Expanded diagram — scroll horizontally to explore</span>
        <button
          type="button"
          className="button button--secondary button--sm"
          onClick={() => dialogRef.current?.close()}
        >
          Close
        </button>
      </div>
      <div ref={contentRef} className="mermaid-lightbox__content" />
    </dialog>
  );
}
