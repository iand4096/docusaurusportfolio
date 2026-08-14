# Taxonomy AI suggestions

Model: `deepseek-v4-flash`

> Advisory only. Repository taxonomy and deterministic validation remain authoritative.

## `docs/case-studies/AMXInspiredSignageComposer.md`

### Suggested metadata

```yaml
type: case-study
audiences:
- technical-writers
- documentation-managers
topics:
- technical-writing
- information-architecture
technologies:
- madcap-flare
- mermaid
- tcp-ip
- vale
- languagetool
lifecycle: current
```

### Rationale

- **type**: The document is a case study describing a documentation project for AMX Composer 5.
- **audiences**: The content is relevant to technical writers and documentation managers as it discusses documentation strategy and tools.
- **topics**: The document focuses on technical writing practices and information architecture for audience-specific documentation.
- **technologies**: MadCap Flare is the primary authoring tool; Mermaid is used for a diagram; TCP/IP is mentioned as required knowledge; Vale and LanguageTool are mentioned as potential improvements.
- **lifecycle**: The content represents current portfolio material and is not marked as historical or archived.

## `docs/case-studies/DocusaurusPortfolio.md`

### Suggested metadata

```yaml
type: case-study
audiences:
- developers
- technical-writers
- documentation-managers
topics:
- docs-as-code
- documentation-engineering
- developer-experience
- technical-writing
technologies:
- docusaurus
- markdown
- mdx
- react
- jsx
- github-actions
- github-pages
- deepseek-api
- python
- requests
- mermaid
- vale
lifecycle: current
```

### Rationale

- **type**: The document describes a project: building a Docusaurus portfolio site, including challenges, approach, deliverables, and outcomes, fitting the case-study type.
- **audiences**: The content is relevant to developers (React, GitHub Actions, APIs), technical writers (docs-as-code, documentation engineering), and documentation managers (workflow and QA).
- **topics**: The document focuses on docs-as-code, documentation engineering, developer experience (portfolio for developers), and technical writing.
- **technologies**: Technologies are materially used or discussed: Docusaurus, Markdown, MDX, React, JSX, GitHub Actions, GitHub Pages, DeepSeek API, Python, Requests, Mermaid, and Vale (mentioned as a future addition).
- **lifecycle**: The content describes current practice and portfolio material, so lifecycle is current.

### Taxonomy expansion proposals

#### `technologies.python` — Python — kind `programming-language`

Python is used in the QA workflow script, but it is not in the existing taxonomy.

Suggested term definition:

```yaml
python:
  label: Python
  description: A general-purpose programming language.
  kind: programming-language
```

Evidence:
- `A documentation QA workflow that uses Python and the `requests` library to call the DeepSeek REST API`

## `docs/case-studies/PaysafeDeveloperJS.md`

### Suggested metadata

```yaml
type: case-study
audiences:
- developers
topics:
- api-documentation
- payments
- technical-writing
technologies:
- paysafe-js
- codepen
- pci-dss
- saq-a
- 3d-secure
- google-pay
- apple-pay
lifecycle: current
```

### Rationale

- **type**: The document is a case study describing the creation of a developer guide for Paysafe.js.
- **audiences**: The primary audience is developers who integrate Paysafe.js into their websites.
- **topics**: The document focuses on API documentation for Paysafe.js, payment integration, and technical writing practices.
- **technologies**: Paysafe.js is the core technology documented; CodePen is used for examples; PCI DSS and SAQ A are compliance standards discussed; 3D Secure, Google Pay, and Apple Pay are mentioned as features covered in the expanded guide.
- **lifecycle**: The case study describes current portfolio material and the guide is publicly available.

## `docs/case-studies/ScalingADeveloperDocsPlatform.md`

### Suggested metadata

```yaml
type: case-study
audiences:
- developers
- documentation-managers
- technical-writers
topics:
- docs-as-code
- documentation-engineering
- developer-experience
- information-architecture
- documentation-governance
technologies:
- codetreedocs
- git
- markdown
- jenkins
- intellij-idea
- twiki
- sphinx
- docker
- vale
- languagetool
- agentic-ai
- spec-driven-development
lifecycle: current
```

### Rationale

- **type**: The document is a detailed account of a project, including challenge, approach, deliverables, and outcome, fitting the case-study content type.
- **audiences**: The content is relevant to developers who use the platform, documentation managers who oversee documentation strategy, and technical writers who create documentation.
- **topics**: The document focuses on docs-as-code, documentation engineering, developer experience, information architecture, and documentation governance, all of which are explicitly discussed.
- **technologies**: The document mentions several technologies that are materially used or discussed, including the custom platform Codetreedocs, Git, Markdown, Jenkins, IntelliJ IDEA, TWiki, Sphinx, Docker, Vale, LanguageTool, agentic AI, and spec-driven development.
- **lifecycle**: The content describes current practice and portfolio material, so it is classified as current.

## `docs/skills/AIandDocumentation.md`

### Suggested metadata

```yaml
type: skill
audiences:
- technical-writers
- developers
- documentation-managers
topics:
- documentation-engineering
- docs-as-code
- technical-writing
- developer-experience
technologies:
- rag
- mcp
- fastmcp
- whisper
- spec-driven-development
lifecycle: current
```

### Rationale

- **type**: The document describes a professional capability in applying AI to documentation, fitting the 'skill' content type.
- **audiences**: The content is relevant to technical writers, developers, and documentation managers who work with AI-assisted documentation.
- **topics**: The document covers documentation engineering, docs-as-code, technical writing, and developer experience through AI applications.
- **technologies**: The document explicitly mentions RAG, MCP, FastMCP, Whisper, and spec-driven development as technologies used.
- **lifecycle**: The content represents current practice and capability, so 'current' is appropriate.

## `docs/skills/DocumentationEngineering.md`

### Suggested metadata

```yaml
type: skill
audiences:
- technical-writers
- documentation-managers
- developers
topics:
- documentation-engineering
- docs-as-code
- technical-writing
- information-architecture
- technical-validation
technologies:
- git
- markdown
- mdx
- jenkins
- github-actions
- docusaurus
- mkdocs
- codetreedocs
- graphviz
- python
- postman
- insomnia
- ocr
- rag
- react
lifecycle: current
```

### Rationale

- **type**: The document describes a professional capability in documentation engineering, fitting the 'skill' content type.
- **audiences**: The content is relevant to technical writers, documentation managers, and developers who work with documentation systems.
- **topics**: The document covers documentation engineering, docs-as-code, technical writing, information architecture, and technical validation.
- **technologies**: The document mentions specific technologies used in documentation engineering, including Git, Markdown, CI/CD tools, static-site generators, and validation tools.
- **lifecycle**: The content represents current practice and capability, so 'current' is appropriate.

### Taxonomy expansion proposals

#### `technologies.python` — Python — kind `programming-language`

Python is mentioned as a language used for migration scripts and tooling, and is a significant technology in the document.

Suggested term definition:

```yaml
python:
  label: Python
  description: A general-purpose programming language.
  kind: programming-language
```

Evidence:
- `Python migration scripts`
- `Python and Java test applications`

## `docs/skills/DocumentationLeadership.md`

### Suggested metadata

```yaml
type: skill
audiences:
- documentation-managers
- technical-writers
topics:
- documentation-engineering
- documentation-governance
- developer-experience
- docs-as-code
- information-architecture
technologies:
- codetreedocs
- git
- docker
lifecycle: current
```

### Rationale

- **type**: The document describes a professional capability in documentation leadership and strategy, fitting the 'skill' content type.
- **audiences**: The content is primarily relevant to documentation managers and technical writers, as it discusses team leadership, strategy, and platform ownership.
- **topics**: The document covers documentation engineering, governance, developer experience, docs-as-code, and information architecture, all of which are explicitly mentioned or implied.
- **technologies**: Codetreedocs is explicitly named as a docs-as-code platform; Git and Docker are mentioned as part of the workflows and infrastructure.
- **lifecycle**: The content represents current professional capability and is not historical or archived.

## `docs/skills/GovernanceDocs.md`

### Suggested metadata

```yaml
type: skill
audiences:
- technical-writers
- documentation-managers
topics:
- documentation-governance
- information-architecture
- docs-as-code
technologies:
- c4-model
- finos-calm
- jira
- ldap
- whisper
- markdown
lifecycle: current
```

### Rationale

- **type**: The document describes a professional capability in governance documentation, fitting the 'skill' content type.
- **audiences**: The content is relevant to technical writers who create governance documentation and documentation managers who oversee governance processes.
- **topics**: The document focuses on governance documentation, information architecture, and docs-as-code practices.
- **technologies**: The document mentions C4 model, FINOS CALM, Jira, LDAP, Whisper, and Markdown as technologies used in governance documentation.
- **lifecycle**: The content represents current professional experience and practices.

## `docs/skills/index.md`

### Suggested metadata

```yaml
type: skill
audiences:
- technical-writers
- documentation-managers
- developers
topics:
- technical-writing
- documentation-engineering
- documentation-governance
- information-architecture
- developer-experience
technologies: []
lifecycle: current
```

### Rationale

- **type**: The page is a skills index page, listing professional capabilities.
- **audiences**: The page targets technical writers, documentation managers, and developers, as it covers technical writing, documentation engineering, and developer documentation.
- **topics**: The page explicitly mentions technical-writing, documentation-engineering, governance, structured-authoring, and developer-documentation capabilities, which map to the selected topics.
- **technologies**: No specific technologies are mentioned in the document content.
- **lifecycle**: The page is a current overview of skills, not historical or archived.

## `docs/skills/InformationArchitecture.md`

### Suggested metadata

```yaml
type: skill
audiences:
- technical-writers
- documentation-managers
topics:
- information-architecture
- documentation-engineering
- docs-as-code
- developer-experience
technologies:
- graphviz
- git
- markdown
- sphinx
- twiki
- rag
lifecycle: current
```

### Rationale

- **type**: The document describes a professional capability in information architecture, fitting the 'skill' content type.
- **audiences**: The content is relevant to technical writers and documentation managers who deal with information architecture and documentation strategy.
- **topics**: The document focuses on information architecture, with supporting topics of documentation engineering, docs-as-code, and developer experience.
- **technologies**: The document mentions Graphviz, Git, Markdown, Sphinx, TWiki, and RAG as technologies used in the described work.
- **lifecycle**: The content represents current professional skills and experience, so 'current' is appropriate.

## `docs/tools/AIandDevTools.md`

### Suggested metadata

```yaml
type: tool
audiences:
- developers
- technical-writers
topics:
- documentation-engineering
- developer-experience
- docs-as-code
technologies:
- spec-driven-development
- claude
- github-copilot
- amp
- mcp
- fastmcp
- rag
- intellij-idea
- pycharm
- vs-code
lifecycle: current
```

### Rationale

- **type**: The page describes a set of tools and techniques used in documentation engineering and software development, fitting the 'tool' content type.
- **audiences**: The content is relevant to developers who use AI and developer tools, and to technical writers who apply these tools in documentation workflows.
- **topics**: The page covers documentation engineering practices, developer experience with AI tools, and docs-as-code approaches such as spec-driven development.
- **technologies**: The page explicitly mentions and describes hands-on experience with AI coding tools (Claude, GitHub Copilot, Amp), MCP and FastMCP, RAG, and IDEs (IntelliJ IDEA, PyCharm, VS Code).
- **lifecycle**: The content describes current practices and tools, so it is classified as current.

## `docs/tools/ContainersAndCloudNative.md`

### Suggested metadata

```yaml
type: skill
audiences:
- system-administrators
- technical-writers
topics:
- documentation-engineering
- technical-validation
technologies:
- docker
- nginx
- pythonanywhere
- linux
- tcp-ip
- openwrt
- wireshark
- kubernetes
- proxmox
- home-assistant
lifecycle: current
```

### Rationale

- **type**: The document describes a professional capability in containers, cloud, and networking, fitting the 'skill' content type.
- **audiences**: The content is relevant to system administrators who manage such environments and technical writers who need to understand infrastructure for documentation platforms.
- **topics**: The document focuses on applying software engineering techniques to documentation platforms and validating integrations, aligning with documentation-engineering and technical-validation.
- **technologies**: The document explicitly mentions Docker, Nginx, PythonAnywhere, Linux, TCP/IP, OpenWrt, Wireshark, Kubernetes, Proxmox, and Home Assistant as technologies used or demonstrated.
- **lifecycle**: The content represents current practical experience and capabilities, so it is classified as current.

## `docs/tools/Diagramming.md`

### Suggested metadata

```yaml
type: skill
audiences:
- technical-writers
- developers
topics:
- technical-writing
- documentation-engineering
- information-architecture
technologies:
- c4-model
- plantuml
- mermaid
- graphviz
- git
- markdown
- visio
- adobe-illustrator
- inkscape
- ocr
- catia
lifecycle: current
```

### Rationale

- **type**: The document describes a professional capability in creating and maintaining technical diagrams, which aligns with the 'skill' content type.
- **audiences**: The content is relevant to technical writers who create diagrams and developers who consume technical documentation with diagrams.
- **topics**: The document covers technical writing practices, documentation engineering (diagrams-as-code), and information architecture (using diagrams for navigation).
- **technologies**: The document explicitly mentions C4 model, PlantUML, Mermaid, Graphviz, Git, Markdown, Visio, Adobe Illustrator, Inkscape, OCR, and CATIA as tools and techniques used.
- **lifecycle**: The content describes current skills and practices, so 'current' is appropriate.

## `docs/tools/DocusaurusAndMkdocs.md`

### Suggested metadata

```yaml
type: tool
audiences:
- technical-writers
- documentation-managers
topics:
- docs-as-code
- documentation-engineering
- developer-experience
technologies:
- docusaurus
- mdx
- react
- jsx
- github-actions
- github-pages
- mkdocs
- twiki
- flexsearch
- vs-code
- languagetool
lifecycle: current
```

### Rationale

- **type**: The document describes tools and technologies used in documentation engineering, fitting the 'tool' content type.
- **audiences**: The content is relevant to technical writers and documentation managers who work with static site generators and documentation platforms.
- **topics**: The document covers docs-as-code practices, documentation engineering, and developer experience aspects of documentation platforms.
- **technologies**: The document explicitly mentions Docusaurus, MDX, React, JSX, GitHub Actions, GitHub Pages, MkDocs, TWiki, FlexSearch, VS Code, and LTeX+ (a LanguageTool-based spell checker).
- **lifecycle**: The content describes current tools and practices, so 'current' is appropriate.

## `docs/tools/GitContinousIntegration.md`

### Suggested metadata

```yaml
type: tool
audiences:
- technical-writers
- developers
topics:
- docs-as-code
- documentation-engineering
- technical-writing
technologies:
- git
- github
- github-actions
- jenkins
- docusaurus
- linux
lifecycle: current
```

### Rationale

- **type**: The document describes a tool page for Git and related CI/CD technologies, fitting the 'tool' content type.
- **audiences**: The content is relevant to technical writers who use Git and CI/CD for documentation, and developers who work with these tools.
- **topics**: The document covers docs-as-code practices, documentation engineering, and technical writing skills.
- **technologies**: The document explicitly mentions Git, GitHub, GitHub Actions, Jenkins, Docusaurus, and Linux as technologies used.
- **lifecycle**: The content represents current skills and practices, so 'current' is appropriate.

## `docs/tools/index.md`

### Suggested metadata

```yaml
type: landing-page
audiences:
- technical-writers
topics:
- documentation-engineering
technologies: []
lifecycle: current
```

### Rationale

- **type**: The page is a landing page that introduces a section and provides navigation to its contents.
- **audiences**: The page is about tools for technical documentation, which is most relevant to technical writers.
- **topics**: The page focuses on tools for creating, maintaining, enhancing, and publishing technical documentation, which falls under documentation engineering.
- **technologies**: No specific technologies are mentioned in the document content.
- **lifecycle**: The page is a current introduction to the tools section, not historical or archived.

# Consolidated taxonomy proposals

## `technologies.python`

Suggested from: `docs/case-studies/DocusaurusPortfolio.md`, `docs/skills/DocumentationEngineering.md`

```yaml
python:
  label: Python
  description: A general-purpose programming language.
  kind: programming-language
```
