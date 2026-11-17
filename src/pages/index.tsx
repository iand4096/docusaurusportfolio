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
    evidenceNote: '2016 company figures; growth excludes acquisition and currency effects.',
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
];

export default function Home(): React.ReactElement {
  return (
    <Layout
      title="Ian Drewett | Technical Writer & Documentation Engineer"
      description="Developer documentation, from enterprise platforms to tested API integrations. Technical writing and documentation engineering by Ian Drewett."
    >
      <main className={styles.home} id="main-content">
        <section className={styles.hero}>
          <p className={styles.eyebrow}>Ian Drewett · Technical Writer & Documentation Engineer</p>
          <h1><span className={styles.headlineAccent}>Developer documentation,</span> from enterprise platforms to tested API integrations.</h1>
          <p className={styles.lead}>
            I write technical documentation, build the platforms that publish it,
            and test the integrations it describes. My experience spans Morgan
            Stanley, Mastercard and Paysafe.
          </p>
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
            <h2 id="search-heading">Building search for this portfolio</h2>
            <p>I deployed a Python search API on Azure using Docker and Terraform.
              It combines keyword and semantic retrieval with taxonomy filters
              and optional AI answers linked to source passages.</p>
          </div>
          <div className={styles.labActions}>
            <Link to="/explore?view=ai-search" className={styles.primary}>Try the search →</Link>
            <Link to="/docs/case-studies/RagSearchCloudArchitecture" className={styles.textLink}>Read the architecture case study →</Link>
          </div>
        </section>

        <section className={styles.about} id="about">
          <div>
            <h2>Writing, engineering and leadership</h2>
            <p>I have an M.Sc. in Computer Science, a degree in Physics and a
              background in software engineering. My documentation work ranges
              from Scala frameworks and payment APIs to developer portals and
              team leadership.</p>
            <p>Explore my <Link to="/docs/apidocumentation">API documentation</Link>,{' '}
              <Link to="/docs/documentationeng">documentation engineering</Link> and{' '}
              <Link to="/docs/docsleadership">leadership experience</Link>.</p>
          </div>
          <div className={styles.contact}>
            <h3>Get in touch</h3>
            <p>For technical-writing and documentation-engineering roles,
              contract work or consultancy enquiries.</p>
            <Link to={linkedin} className={styles.textLink}>Contact me on LinkedIn ↗</Link>
          </div>
        </section>
      </main>
    </Layout>
  );
}
