import React from 'react';
import CapabilityCard from '@site/src/components/CapabilityCard';

export default function PhilosophyOverview() {
  return (
    <CapabilityCard autoColumns heading="h2" items={[
      {
        title: 'Writing for readers',
        icon: 'book-open',
        summary: <ul>
          <li><a href="#start-with-empathy-for-the-reader">Have empathy for the reader</a></li>
          <li><a href="#verify-what-the-software-actually-does">Verify software behaviour</a></li>
          <li><a href="#use-evidence-to-inform-decisions">Use evidence to inform decisions</a></li>
        </ul>,
      },
      {
        title: 'Designing knowledge systems',
        icon: 'gears',
        summary: <ul>
          <li><a href="#make-good-contributions-easy">Make contributions easy</a></li>
          <li><a href="#maintain-one-authoritative-source-for-each-fact">Maintain an authoritative source</a></li>
          <li><a href="#build-quality-checks-into-the-workflow">Build in quality checks</a></li>
          <li><a href="#govern-knowledge-so-people-can-find-and-trust-it">Govern knowledge</a></li>
        </ul>,
      },
    ]} />
  );
}
