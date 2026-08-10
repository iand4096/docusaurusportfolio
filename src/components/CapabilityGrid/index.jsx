import React, {useEffect, useRef} from 'react';
import styles from './styles.module.css';

export default function CapabilityGrid({
  children,
  variant = 'default',
}) {
  const gridRef = useRef(null);

  useEffect(() => {
    if (variant !== 'checklist' || !gridRef.current) {
      return;
    }

    const root = gridRef.current;
    let frameId;

    const measureItems = () => {
      cancelAnimationFrame(frameId);

      frameId = requestAnimationFrame(() => {
        const items = root.querySelectorAll(':scope > ul > li');

        items.forEach((item) => {
          const itemRect = item.getBoundingClientRect();

          let furthestTextRight = 0;

          /*
           * Measure only actual text nodes.
           * This gives us the rendered width of every
           * line of wrapped text.
           */
          const walker = document.createTreeWalker(
            item,
            NodeFilter.SHOW_TEXT,
            {
              acceptNode(node) {
                return node.nodeValue.trim()
                  ? NodeFilter.FILTER_ACCEPT
                  : NodeFilter.FILTER_REJECT;
              },
            }
          );

          while (walker.nextNode()) {
            const range = document.createRange();

            range.selectNodeContents(walker.currentNode);

            for (const rect of range.getClientRects()) {
              const right = rect.right - itemRect.left;

              furthestTextRight = Math.max(
                furthestTextRight,
                right
              );
            }
          }

          if (furthestTextRight > 0) {
            item.style.setProperty(
              '--check-x',
              `${Math.ceil(furthestTextRight)}px`
            );

            item.dataset.checkMeasured = 'true';
          }
        });
      });
    };

    measureItems();

    const resizeObserver = new ResizeObserver(measureItems);
    resizeObserver.observe(root);

    window.addEventListener('resize', measureItems);

    if (document.fonts?.ready) {
      document.fonts.ready.then(measureItems);
    }

    return () => {
      cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
      window.removeEventListener('resize', measureItems);
    };
  }, [variant, children]);

  return (
    <div
      ref={gridRef}
      className={styles.grid}
      data-variant={variant}
    >
      {children}
    </div>
  );
}