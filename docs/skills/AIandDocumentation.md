---
title: AI & Documentation
sidebar_position: 9
slug: /aianddocs

sidebar_custom_props:
  skillCard:
    tag: AI for documentation
    description: Applying AI to documentation engineering, authoring, retrieval and automation, with
      technical validation and human review.
    highlights:
      - AI-assisted documentation from Jira and SME input
      - SKILL.md guidance for consistent AI-authored docs
      - RAG and metadata-aware retrieval
      - Experimental MCP servers with FastMCP
    ariaLabel: Explore my AI for documentation skills

type:
  - skill

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
  - jira
  - claude
  - github-copilot
  - amp
  - agentic-ai
  - markdown

audiences:
  - technical-writers
  - documentation-managers
  - developers

lifecycle:
  - current
tags:
  - agentic-ai
  - amp
  - claude
  - developer-experience
  - docs-as-code
  - documentation-engineering
  - fastmcp
  - github-copilot
  - jira
  - markdown
  - mcp
  - rag
  - spec-driven-development
  - technical-writing
  - whisper
---

I use AI selectively for documentation authoring, retrieval, quality assurance, and documentation-platform development. I manually review generated text and code before using it.

## AI-assisted authoring

I created **SKILL.md** guidance for developers using AI coding agents to generate documentation, so generated content matched local documentation conventions and style guidelines. I wrote guidelines to clarify that generated content must be manually reviewed and that responsibility for the final change would remain with the person committing it. Additionally, I used AI personally for lower-risk documentation tasks such as grammar and style review, diagram generation, and other work where I could independently check the output.

## AI-assisted development

I have used agentic coding assistants including **Amp, Claude, and GitHub Copilot** while extending the documentation platform. Examples include adding PlantUML support, fixing problems with documentation link checking, and creating tooling for tasks such as content migration. For larger changes. I generally work from a written specification by defining the requirements in Markdown first and then use AI to help generate or modify the implementation. Finally, I test the resulting code extensively before accepting it.

## Retrieval and RAG

I integrated documentation with a central **RAG-based search system** by generating the sitemap and metadata required for indexing as part of the documentation CI/CD process. During this work, I found cases where deprecated APIs could still appear in RAG search results. I proposed using lifecycle metadata and retrieval filtering so deprecated material would only be returned when the user specifically requested it.

## Validation and governance

AI-generated documentation is reviewed by a person before publication rather than being published directly. On my portfolio site, I have also experimented with AI-assisted documentation quality checks to flag issues such as repetition and possible grammar problems. I use these alongside deterministic checks such as link checking rather than replacing them.

## Local AI and privacy

Where source material could not be sent to external services, I have used locally hosted AI tools instead. One example was a pilot using **Whisper** to assist with transcription of sensitive software architecture discussions, reducing the amount of manual transcription required while keeping the source material local.

## MCP and AI tooling experiments

I built an experimental **Model Context Protocol (MCP)** server with **FastMCP** to test whether AI agents could call documentation tools such as link checkers etc.