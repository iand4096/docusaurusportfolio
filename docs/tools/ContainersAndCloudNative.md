---
title: Containers and Cloud
sidebar_position: 9
slug: /containersandcloud
sidebar_custom_props:
  sampleCard:
    tag: Containers and cloud
    description: >-
      Deploying documentation platforms and Python APIs with Docker, Azure and
      Terraform, supported by Linux administration and network troubleshooting.
    highlights:
      - Led a Docker/Nginx documentation-platform migration; cut build time by approximately 15 minutes
      - Built and deployed a Python search API on Azure Container Apps using Terraform
    ariaLabel: Explore my containers and cloud skills
type:
  - tool
audiences:
  - technical-writers
  - documentation-managers
topics:
  - documentation-engineering
  - docs-as-code
  - technical-validation
technologies:
  - azure-container-apps
  - azure-container-registry
  - azure-log-analytics
  - azure-managed-identity
  - docker
  - nginx
  - linux
  - pythonanywhere
  - tcp-ip
  - openwrt
  - wireshark
  - kubernetes
  - terraform
lifecycle:
  - current
tags:
  - azure-container-apps
  - azure-container-registry
  - azure-log-analytics
  - azure-managed-identity
  - docker
  - docs-as-code
  - documentation-engineering
  - kubernetes
  - linux
  - nginx
  - openwrt
  - pythonanywhere
  - tcp-ip
  - technical-validation
  - terraform
  - wireshark
---

## Containers, cloud and networking {/* #containers-cloud-and-networking */}

Practical experience using **Docker, Azure, Terraform, Linux and networking** to deploy documentation platforms and cloud applications and support API integration testing, with basic exposure to Kubernetes.

### Docker and containers {/* #docker-and-containers */}

* Led a project to migrate a large internal documentation platform to **Docker**, working with a software engineer from the central digital-modernisation team.
* Defined documentation-platform requirements and helped migrate the web hosting and publishing environment to **Nginx running in Docker**. Built redirect logic so that old links continued to work.
* Identified a build-performance issue caused by copying approximately **3,200 generated documentation pages into the container**.
* Proposed serving the generated documentation from an attached file system instead, reducing build time by approximately **15 minutes**.
* Gained experience troubleshooting containerised documentation builds.
* Built and deployed a containerised Python search API, packaging its embedding model and search indexes, with **Docker Compose** for local development.
* Built a personal Kubernetes cluster on Proxmox.

### Cloud deployment and integration testing {/* #cloud-hosted-integration-testing */}

* Used **PythonAnywhere** to host generated public documentation for SME review.
* Built externally accessible Python integrations to receive and test **webhooks** that could not reach internal development environments due to the corporate firewall.
* Used hosted environments to validate API and asynchronous integration behaviour.
* Designed and provisioned the Azure deployment for my [RAG search application](../case-studies/RagSearchCloudArchitecture.md) using **Terraform**, including Container Apps, a private image registry, managed identity, secret configuration and operational logging.

### Linux and networking {/* #linux-and-networking */}

* Comfortable working in **Linux/Unix environments** and troubleshooting differences between local and CI builds. Extensive experience with Bash, vi, ssh, grep, sed, cURL, etc.
* Practical and theoretical understanding of **TCP/IP networking** developed during my M.Sc. in Computer Science and while documenting networked audio/video and digital-signage systems.
* Personal experience configuring **OpenWrt**, firewalls and network services.
* Basic use of **Wireshark** and **Fiddler** for network troubleshooting.
