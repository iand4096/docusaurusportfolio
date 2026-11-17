import React from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import styles from './index.module.css';

const linkedin = 'https://www.linkedin.com/in/ian-drewett/';
const projects = [
  {
    employer: 'Morgan Stanley',
    title: 'Scaling an enterprise documentation platform',
    description: 'Led the design and evolution of a docs-as-code platform for quantitative analysts and developers, growing from 700 to more than 3,200 pages.',
    evidence: '3,200+ pages · ~900 legacy pages converted',
    href: '/docs/case-studies/scalingdeveloperdocs',
    action: 'Read case study',
  },
  {
    employer: 'Paysafe',
    title: 'Building a unified Developer Center',
    description: 'Led delivery of a unified Developer Center for a rapidly growing, API-first payments business, bringing together Optimal Payments and Skrill API, SDK and integration documentation.',
    evidence: '$1bn+ annual revenue · 21% growth',
    evidenceNote: 'Company figures; growth excludes acquisition and currency effects.',
    href: '/docs/case-studies/paysafedevcenter',
    action: 'Read case study',
  },
  {
    employer: 'Mastercard',
    title: 'Testing and documenting MDES integrations',
    description: 'Built a Python integration to validate merchant tokenisation workflows, including encryption and asynchronous webhooks, then authored the MDES for Merchants Use-Case Guide.',
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
      description="Developer documentation and knowledge systems for people and AI. Technical writing, documentation platforms, governed metadata and tested API integrations by Ian Drewett."
    >
      <main className={styles.home} id="main-content">
        <section className={styles.hero}>
          <p className={styles.eyebrow}>Ian Drewett · Technical Writer & Documentation Engineer</p>
          <h1><span className={styles.headlineAccent}>Developer documentation</span> and knowledge systems for people and AI.</h1>
          <p className={styles.lead}>
            I help companies explain complex products and prepare technical
            knowledge for AI-assisted discovery. My work combines technical
            writing, documentation platforms, governed metadata and tested API
            integrations.
          </p>
          <p className={styles.experience}>Experience at Morgan Stanley, Mastercard and Paysafe.</p>
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
                <p className={styles.employer}>{project.employer}</p>
                <h3>{project.title}</h3>
                <p className={styles.description}>{project.description}</p>
                <p className={styles.evidence}>{project.evidence}</p>
                {project.evidenceNote && <p className={styles.evidenceNote}>{project.evidenceNote}</p>}
                <Link to={project.href} className={styles.textLink}>{project.action} →</Link>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.lab} aria-labelledby="search-heading">
          <div>
            <p className={styles.eyebrow}>Independent project</p>
            <h2 id="search-heading">Putting AI-ready knowledge into practice</h2>
            <p>This portfolio connects structured content and a canonical taxonomy
              with metadata validation, hybrid keyword and semantic retrieval,
              and lifecycle filtering. Optional AI answers link to the retrieved
              source passages so readers can inspect the evidence.</p>
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
            <h2>Technical writing, documentation engineering and AI-ready knowledge systems</h2>
            <p>I have an M.Sc. in Computer Science, a degree in Physics and a
              background in software engineering. My documentation work ranges
              from Scala frameworks and payment APIs to developer portals and
              team leadership. I also design governed content structures and
              validation tools that make technical knowledge easier to maintain,
              retrieve and trace to its sources.</p>
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
            <Link to={linkedin} className={styles.textLink}>Contact me on LinkedIn ↗</Link>
          </div>
        </section>
      </main>
    </Layout>
  );
}
