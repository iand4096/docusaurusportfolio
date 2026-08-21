---
title: MadCap Flare
sidebar_position: 8
slug: /flare
sidebar_custom_props:
  skillCard:
    tag: Structured authoring
    description: Advanced single-sourcing, custom styling, publishing automation, Git integration, content migration and complex output troubleshooting.
    highlights:
      - Nearly eight years of experience
      - HTML and PDF single-sourcing
      - C# and REST API automation
      - 131 community-forum contributions
    ariaLabel: Explore my MadCap Flare skills
---

import CapabilityGrid from '@site/src/components/CapabilityGrid';

I am a MadCap Flare specialist with nearly eight years of experience using Flare at AMX, Monitise (now Fiserv) and Paysafe.

## Core flare skills

<CapabilityGrid variant="checklist">

- Topic-based authoring
- Tables of contents
- Targets and build configurations
- Applying and maintaining stylesheets and templates
- Snippets and variables
- Hyperlinks and cross-references
- Conditional text
- Tables and images
- HTML and PDF publishing

</CapabilityGrid>

## Advanced flare skills

<CapabilityGrid>

- **Advanced single-sourcing**  
  Conditional single-sourcing across products, platforms and outputs

- **Multi-product documentation**  
  Multi-product and multi-platform documentation and cross-project linking

- **Customisation**  
  Custom CSS, XML and output-template development

- **Version control and CI**  
  Git-based collaboration and continuous integration

- **Integration**  
  CMS and search integration

- **Troubleshooting**  
  Complex output troubleshooting

</CapabilityGrid>

I applied these capabilities to the automation, integration and migration projects described in the [Flare Automation, Integration and Migration](#automation) section.

## Flare community contributions

I have published 131 posts on the MadCap Flare user forum under the username **iand**, contributing answers, troubleshooting guidance and practical workarounds for other Flare users.

One example is my proposed workaround for a long-running Flare limitation: [how to support code syntax highlighting in both HTML and PDF output](https://forums.madcapsoftware.com/viewtopic.php?p=99025&hilit=iand#p99025).

See all [posts](https://forums.madcapsoftware.com/search.php?st=0&sk=t&sd=d&sr=posts&author_id=7956)

## Flare automation, integration and migration {/* #automation */}

At Paysafe, I integrated Flare with development, publishing and review systems as part of a broader documentation tool chain used to manage all the non-API-reference documentation on the launch version of the [Paysafe Developer Centre](https://developer.paysafe.com).

My work included:

* **Building a Flare post-build automation workflow** that:

  * Automatically published generated HTML output to the cloud-based hosting platform [PythonAnywhere](https://en.wikipedia.org/wiki/PythonAnywhere) for review.
  * Integrated [Hypothes.is](https://h.readthedocs.io/projects/client/en/latest/publishers/embedding.html) with the hosted documentation, allowing product specialists and subject-matter experts to annotate rendered pages directly. You can [see Hypothes.is in action on this page](https://hyp.is/0K4rskZkEeyeeCv6boS4Zg/h.readthedocs.io/en/latest/developing/administration/); all text highlighted in yellow has annotations.

* **Developing scripts to migrate developer documentation from Confluence to MadCap Flare**, including:

  * Extracting, cleaning and restructuring legacy Confluence content into Flare-compatible XHTML topics
  * Applying templates, styles and information architecture
  * Preserving links and reusable content where possible

In another role, I built a **C# release-notes tool** that:

  1. Queried the Jira REST API for tickets tagged to a specific release
  2. Extracted and transformed issue data
  3. Parsed and generated Flare-compatible XHTML
  4. Created consistently structured release documentation using a predefined topic template
