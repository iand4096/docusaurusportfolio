# Source notes

Reviewed 15 November 2026. These are primary project documentation or established security-community guidance. The skill combines their recommendations into workflow defaults; it does not reproduce a mandatory external standard. Recheck version-specific commands before use.

| Source | Guidance used |
| --- | --- |
| [OWASP Secure Coding with AI](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html) | AI-hallucinated dependencies, indirect prompt injection through development material, persistent rules-file changes, MCP supply-chain exposure, and review of agent-generated tests and changes. |
| [OWASP AI Agent Security](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html) | Minimum necessary tool permissions, prompt-injection boundaries, credential protection, memory poisoning and bounded autonomy. |
| [OpenAI agent approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security) | Distinguishes execution restrictions from approval policies and documents separately governed command, browser and connected-tool access. A skill is guidance, not an enforcement mechanism. |
| [OWASP Software Supply Chain Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html#mitigating-dependency-threats) | Evaluate suppliers, inventory and monitor dependencies, use reviewed locked versions, and account for build tools as part of the supply chain. |
| [OWASP NPM Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/NPM_Security_Cheat_Sheet.html) | Verify names against upstream projects to counter typosquatting and AI-hallucinated packages; restrict lifecycle scripts and credentials; inspect unfamiliar checkout configuration; use disposable execution environments for untrusted code. |
| [`npm ci`](https://docs.npmjs.com/cli/v11/commands/npm-ci/) | Lockfile-based clean installs, manifest-mismatch failures, replacement of existing installed modules, and the distinction between suppressed installation hooks and explicitly invoked scripts. Consult documentation matching the installed CLI before using script allowlists. |
| [`npm install`](https://docs.npmjs.com/cli/v11/commands/npm-install/) | Exact-version installation and manifest/lock management. Temporary installations should retain their dependency resolution rather than disable lockfile creation. |
| [`npm audit`](https://docs.npmjs.com/cli/v11/commands/npm-audit/) | Advisory scanning, registry-signature/provenance checks, metadata submission to registries, and the fact that automated fixes perform installations and may change dependencies. |
| [`pip secure installs`](https://pip.pypa.io/en/stable/topics/secure-installs/) | Fully pinned, hashed direct and transitive requirements; binary-only installation to avoid source-distribution build execution. These controls do not make installed code safe to execute. |
| [`pip install: additional indexes`](https://pip.pypa.io/en/stable/cli/pip_install/#examples) | Explicit warning that private-package installation with public fallback through `--extra-index-url` permits dependency-confusion attacks. |
| [Python venv](https://docs.python.org/3/library/venv.html) | Separate, disposable Python package environments instead of modifying the system installation. This is package isolation, not a security sandbox. |
| [SLSA 1.2: verifying artifacts](https://slsa.dev/spec/v1.2/verifying-artifacts) | Validate signed provenance against trusted identities and expected artifact/build information, rather than assuming that the presence of provenance proves authenticity. |

The defaults for keeping one-off tools outside project manifests, avoiding automatic `latest` resolution, retaining temporary lockfiles, limiting exceptions and reporting test-tool versions are this skill's practical application of the guidance. They are not presented as universal commands required by every source.

No dependency audit of the portfolio or retrospective verification of earlier downloads was performed as part of preparing this proposal.
