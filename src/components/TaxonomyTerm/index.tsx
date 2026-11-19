import React, {useEffect, useId, useLayoutEffect, useRef, useState} from 'react';
import styles from './styles.module.css';

export default function TaxonomyTerm({children, definition}: {children: string; definition: string}) {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const tooltip = useRef<HTMLSpanElement>(null);
  const [open, setOpen] = useState(false);

  useLayoutEffect(() => {
    const button = trigger.current;
    const popup = tooltip.current;
    if (!open || !button || !popup) return;

    function positionTooltip() {
      if (!button || !popup) return;
      const term = button.getBoundingClientRect();
      const {width, height} = popup.getBoundingClientRect();
      const margin = 8;
      const left = Math.max(margin, Math.min(term.left, document.documentElement.clientWidth - width - margin));
      const top = term.top - height >= margin ? term.top - height : term.bottom;
      popup.style.left = `${left}px`;
      popup.style.top = `${top}px`;
    }

    positionTooltip();
    window.addEventListener('resize', positionTooltip);
    window.addEventListener('scroll', positionTooltip, true);
    return () => {
      window.removeEventListener('resize', positionTooltip);
      window.removeEventListener('scroll', positionTooltip, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', dismiss);
    return () => document.removeEventListener('keydown', dismiss);
  }, [open]);

  return (
    <span
      onPointerEnter={event => {if (event.pointerType === 'mouse') setOpen(true);}}
      onPointerLeave={() => {if (document.activeElement !== trigger.current) setOpen(false);}}
    >
      <button
        ref={trigger}
        type="button"
        className={styles.term}
        aria-describedby={id}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={event => {
          event.currentTarget.focus({preventScroll: true});
          setOpen(true);
        }}
      >{children}</button>
      <span ref={tooltip} className={styles.tooltip} id={id} role="tooltip" hidden={!open}>{definition}</span>
    </span>
  );
}
