import React, {type ReactNode, useEffect, useId, useRef, useState} from 'react';
import styles from './styles.module.css';

export type EvidenceItem = Readonly<{value: string; label: string; emphasis?: 'metric'; labelStyle?: 'note'}>;
export type SummaryEvidence = readonly [EvidenceItem]
  | readonly [EvidenceItem, EvidenceItem]
  | readonly [EvidenceItem, EvidenceItem, EvidenceItem]
  | readonly [EvidenceItem, EvidenceItem, EvidenceItem, EvidenceItem];

export type CaseStudySummaryProps = Readonly<{
  employer: string;
  industry: string;
  projectType: string;
  summary: string;
  summaryUnderline?: string;
  role: string;
  scope: string;
  decision: string;
  decisionLabel?: 'Key decision' | 'Key approach';
  deliverables: string;
  evidenceTitle: string;
  evidence: SummaryEvidence;
  evidenceNote?: string;
}>;

const preferenceKey = 'case-study-summaries-hidden';
const preferenceEvent = 'case-study-summary-preference';
let sessionHidden = false;

function readPreference(): boolean {
  try {
    return window.localStorage.getItem(preferenceKey) === 'true';
  } catch {
    return sessionHidden;
  }
}

/** Editorial overview. All content is present in server-rendered HTML. */
export default function CaseStudySummary({
  employer, industry, projectType, summary, summaryUnderline, role, scope, decision,
  decisionLabel = 'Key decision', deliverables, evidenceTitle, evidence, evidenceNote,
}: CaseStudySummaryProps): ReactNode {
  const underlineStart = summaryUnderline ? summary.indexOf(summaryUnderline) : -1;
  const root = useRef<HTMLElement>(null);
  const contentId = useId();
  const [hidden, setHidden] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setHidden(readPreference());
    setReady(true);
    const onPreference = (event: Event) => setHidden((event as CustomEvent<boolean>).detail);
    const onStorage = (event: StorageEvent) => {
      if (event.key === preferenceKey || event.key === null) setHidden(readPreference());
    };
    window.addEventListener(preferenceEvent, onPreference);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(preferenceEvent, onPreference);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  function toggleSummary() {
    const next = !hidden;
    sessionHidden = next;
    try {
      window.localStorage.setItem(preferenceKey, String(next));
    } catch {
      // Keep the control usable when browser storage is unavailable.
    }
    window.dispatchEvent(new CustomEvent(preferenceEvent, {detail: next}));
  }

  function skipToContent() {
    const section = root.current;
    if (!section) return;
    const headings = section.closest('article')?.querySelectorAll<HTMLElement>('h2, h3');
    const heading = Array.from(headings ?? []).find(candidate =>
      Boolean(section.compareDocumentPosition(candidate) & Node.DOCUMENT_POSITION_FOLLOWING));
    if (!heading) return;
    const temporaryTabIndex = !heading.hasAttribute('tabindex');
    if (temporaryTabIndex) {
      heading.setAttribute('tabindex', '-1');
      heading.addEventListener('blur', () => heading.removeAttribute('tabindex'), {once: true});
    }
    heading.classList.add(styles.skipTarget);
    heading.addEventListener('blur', () => heading.classList.remove(styles.skipTarget), {once: true});
    heading.focus({preventScroll: true});
    heading.scrollIntoView({block: 'start'});
  }

  return (
    <section ref={root} className={`${styles.root} ${hidden ? styles.collapsed : ''}`} aria-label="Project overview">
      <div className={styles.toolbar}>
        <p className={styles.eyebrow} hidden={hidden}>Project overview</p>
        <div className={styles.actions} hidden={!ready}>
          <button type="button" className={styles.control} onClick={skipToContent} hidden={hidden}>
            Skip to case study <span aria-hidden="true">↓</span>
          </button>
          <button type="button" className={styles.control} onClick={toggleSummary}
            aria-expanded={!hidden} aria-controls={contentId}
            aria-describedby={`${contentId}-preference`}
            title={`${hidden ? 'Show' : 'Hide'} summaries across all case studies. Saved in this browser.`}>
            {hidden ? 'Show summaries' : 'Hide summaries'}
          </button>
          <span id={`${contentId}-preference`} className="sr-only">
            Applies to all case studies. Your preference is saved in this browser when storage is available.
          </span>
        </div>
      </div>
      <div id={contentId} hidden={hidden}>
        <ul className={styles.context} aria-label="Project context">
          <li>{employer}</li>
          <li>{industry}</li>
          <li>{projectType}</li>
        </ul>
        <p className={styles.summary}>{underlineStart >= 0 && summaryUnderline ? <>
          {summary.slice(0, underlineStart)}
          <span className={styles.underlined}>{summaryUnderline}</span>
          {summary.slice(underlineStart + summaryUnderline.length)}
        </> : summary}</p>
        <dl className={styles.details}>
          {[
            ['My role', role], ['Project scope', scope],
            [decisionLabel, decision], ['Deliverables', deliverables],
          ].map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        <div className={styles.evidence}>
          <p className={styles.eyebrow}>{evidenceTitle}</p>
          <dl className={styles.evidenceItems}>
            {evidence.map(({value, label, emphasis, labelStyle}) => (
              <div key={`${value}-${label}`} className={emphasis === 'metric' ? styles.metric : undefined}>
                <dt>{value.includes('\n') ? (
                <ul className={styles.evidenceLines}>
                  {value.split('\n').map(line => <li key={line}>{line}</li>)}
                </ul>
              ) : value}</dt>
                <dd className={labelStyle === 'note' ? styles.evidenceNote : undefined}>{label}</dd>
              </div>
            ))}
          </dl>
          {evidenceNote && <p className={styles.note}>{evidenceNote}</p>}
        </div>
      </div>
    </section>
  );
}
