import React from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import styles from './index.module.css';

const linkedin = 'https://www.linkedin.com/in/ian-drewett/';
const companySites: Record<string, string> = {
  'Morgan Stanley': 'https://www.morganstanley.com/',
  Mastercard: 'https://www.mastercard.com/',
  Paysafe: 'https://www.paysafe.com/',
};
const projects = [
  {
    employer: 'Morgan Stanley',
    title: 'Engineering and scaling an enterprise documentation platform',
    description: 'Led the design and evolution of a docs-as-code platform and Developer portal for quantitative analysts and developers, including publishing, migration and contributor workflows. Grew from 700 to more than 3,200 pages.',
    evidence: '3,200+ pages · ~900 legacy pages converted',
    href: '/docs/case-studies/scalingdeveloperdocs',
    action: 'Read case study',
  },
  {
    employer: 'Paysafe',
    title: 'Building a unified Developer Center',
    description: <>Led delivery of a <a href="https://developer.paysafe.com/en/">public Developer Center</a> for a <span className={styles.underlined}>rapidly growing</span>, API-driven payments business, bringing together <a href="https://www.paysafe.com/us-en/paysafegroup/news/detail/optimal-payments-becomes-paysafe-in-game-changing-global-rebrand/">Optimal Payments</a> and <a href="https://www.skrill.com/">Skrill</a> API, SDK and integration documentation.</>,
    evidence: '$1bn+ annual revenue · 21% growth*',
    evidenceNote: 'Company figures; 21% excludes acquisition and currency effects.',
    href: '/docs/case-studies/paysafedevcenter',
    action: 'Read case study',
  },
  {
    employer: 'Mastercard',
    title: 'Testing and documenting MDES integrations',
    description: <>Built a Python integration to validate merchant tokenisation workflows, including encryption and asynchronous webhooks, then authored the MDES for Merchants Use-Case Guide. Mastercard’s Digital Enablement Service (MDES) is one of the technologies behind <a href="https://www.apple.com/apple-pay/">Apple Pay</a>.</>,
    evidence: 'Python integration · Secure payment workflows',
    href: '/docs/docs-samples/MDES4Merchants',
    action: 'Read documentation sample',
  },
  {
    employer: 'Independent project',
    title: 'Governing knowledge with a canonical taxonomy',
    description: 'Built a shared vocabulary for structured documentation, connecting metadata validation, authoring tools, navigation and retrieval. Content lifecycle values and reviewed taxonomy changes keep classification controlled.',
    evidence: 'Canonical taxonomy · Metadata validation · Lifecycle controls',
    href: '/docs/case-studies/TaxonomyGovernance',
    action: 'Read case study',
  },
];

export default function Home(): React.ReactElement {
  return (
    <Layout
      title="Ian Drewett | Technical Writer & Documentation Engineer"
      description="Technical writing. Documentation engineering. AI-ready knowledge. User workflows, APIs, developer frameworks and governed content by Ian Drewett."
    >
      <main className={styles.home} id="main-content">
        <section className={styles.hero}>
          <p className={styles.identity}>Ian Drewett · Lead Technical Writer & Documentation Engineer</p>
          <h1><span className={styles.headlineAccent}>Technical writing.</span> Documentation engineering. AI-ready knowledge.</h1>
          <p className={styles.lead}>
            I help companies explain complex software, from user workflows to
            APIs and developer frameworks. I also engineer documentation platforms
            and prepare technical knowledge for AI discovery.
            My work combines technical writing, content strategy, docs-as-code, tested API
            integrations and governed content.
          </p>
          <p className={styles.experience}>Experience at <a href={companySites['Morgan Stanley']}>Morgan Stanley</a>,{' '}
            <a href={companySites.Mastercard}>Mastercard</a> and <a href={companySites.Paysafe}>Paysafe</a>.</p>
          <div className={styles.actions}>
            <a href="#case-studies" className={styles.primary}>Explore selected work ↓</a>
            <Link to={linkedin} className={styles.textLink}>Connect on LinkedIn ↗</Link>
          </div>
        </section>

        <section className={styles.work} id="case-studies">
          <div className={styles.sectionHeading}>
            <h2>Selected work</h2>
            <Link to="/explore?view=browse&contentType=case-study&contentType=doc-sample" className={styles.textLink}>Browse all work →</Link>
          </div>
          <div className={styles.projects}>
            {projects.map(project => (
              <article className={styles.project} key={project.employer}>
                <p className={styles.employer}>{companySites[project.employer]
                  ? <a href={companySites[project.employer]}>{project.employer}</a>
                  : project.employer}</p>
                <h3>{project.title}</h3>
                <p className={styles.description}>{project.description}</p>
                <div className={styles.evidenceRow}>
                  <p className={styles.evidence}>{project.evidence}</p>
                  {project.evidenceNote && <p className={styles.evidenceNote}>{project.evidenceNote}</p>}
                </div>
                <Link to={project.href} className={`${styles.textLink} ${styles.projectLink}`}
                  aria-label={`${project.action}: ${project.title}`}>{project.action} →</Link>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.lab} aria-labelledby="search-heading">
          <div>
            <p className={styles.eyebrow}>Independent project</p>
            <h2 id="search-heading">Putting AI-ready knowledge into practice</h2>
            <p>This portfolio brings documentation engineering and knowledge
              governance together: structured content, automated metadata
              validation, hybrid retrieval and source-linked AI answers. A
              canonical taxonomy and lifecycle filters govern which passages
              are retrieved, and readers can inspect the original sources.</p>
            <p className={styles.evaluation}>The search API is deployed on Azure using Docker and Terraform.
              Evaluation of retrieval relevance and answer accuracy against a
              representative question set is planned.</p>
          </div>
          <div className={styles.labActions}>
            <Link to="/explore?view=ai-search" className={styles.primary}>Try the search →</Link>
            <Link to="/docs/case-studies/RagSearchCloudArchitecture" className={styles.textLink}>Read the architecture case study →</Link>
          </div>
        </section>

        <section className={styles.about} id="about">
          <div>
            <h2>Experience and approach</h2>
            <p>I have an M.Sc. in Computer Science, a degree in Physics and a
              background in software engineering. My documentation work ranges
              from Scala frameworks and payment APIs to developer portals and
              team leadership. I also design governed content structures and
              validation tools that make technical knowledge easier to maintain,
              retrieve and trace to its sources.{' '}
              <Link to="/docs/case-studies/philosophy" className={`${styles.philosophyLink} ${styles.accentLink}`}>
                Read my documentation and knowledge management philosophy →
              </Link>
            </p>
            <p>Explore my <Link to="/docs/apidocumentation">API documentation</Link>,{' '}
              <Link to="/docs/documentationeng">documentation engineering</Link>,{' '}
              <Link to="/docs/case-studies/TaxonomyGovernance">knowledge governance</Link> and{' '}
              <Link to="/docs/docsleadership">leadership experience</Link>.</p>
          </div>
          <div className={styles.contact}>
            <h3>Get in touch</h3>
            <p>I’m interested in roles involving technical writing, documentation
              engineering, knowledge architecture, content governance and AI
              knowledge systems, as well as contract work and consultancy.</p>
            <Link to={linkedin} className={`${styles.textLink} ${styles.accentLink}`}>Contact me on LinkedIn ↗</Link>
          </div>
        </section>
      </main>
    </Layout>
  );
}
