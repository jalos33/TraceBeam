---
name: dependency-security-audit
description: This skill should be used when the user asks to "add a dependency", "add a package", "install a library", proposes a new pip/npm/cargo package for LanMonitor, or when Claude is about to write a new entry into requirements.txt/pyproject.toml/package.json for this project. Enforces the project's open-source-only, no-known-CVE constraint before any dependency is added.
version: 0.1.0
---

# Dependency Security Audit (LanMonitor)

LanMonitor is a cross-platform (Windows/Mac/Linux) rewrite of the WiPie LAN
monitor. Two hard constraints apply to every dependency added to this
project: it must be open source (OSI-approved license), and it must carry no
known CVEs or active supply-chain red flags at the time it's added.

## When this applies

Trigger before adding anything to `requirements.txt`, `pyproject.toml`,
`package.json`, or any build-time tool (e.g. packaging tools like
PyInstaller). Applies to new dependencies and to version bumps of existing
ones. Does not apply to stdlib-only changes.

## Procedure

1. **Identify the exact package and version** being proposed.
2. **Check the license.** Look up the package's own PyPI/npm page or GitHub
   repo (don't trust `pip show`'s License field alone — it's often blank or
   wrong). Confirm it's OSI-approved (MIT, BSD, Apache-2.0, MPL-2.0, LGPL,
   GPL). Flag copyleft licenses (GPL, LGPL) explicitly to the user — they're
   open source and fine to use as a normal dependency, but modifying the
   library's own source and redistributing that modified source would carry
   share-back obligations. Using it unmodified via pip/npm import does not.
3. **Run the CVE/supply-chain check** via `scripts/audit_dependency.sh
   <ecosystem> <package>` (ecosystem is `pip` or `npm`). It runs `pip-audit`
   or `npm audit` against a scratch install and reports known
   vulnerabilities.
4. **Check maintenance signal**: last release date, single vs. multiple
   maintainers, open issue/PR backlog. A single-maintainer package isn't
   disqualifying (much of the Python ecosystem is), but note it — it affects
   how quickly a future CVE would get patched.
5. **Prefer pure-language implementations over shelling out to OS binaries**
   when a cross-platform choice exists (this project's own precedent:
   `icmplib` replacing subprocess calls to `ping`/`mtr`/`traceroute`, which
   differ per OS and don't all exist on Windows). Fewer OS-specific code
   paths means smaller attack surface and less platform-conditional bugs.
6. **Prefer fewer total dependencies over more.** Adding a package that pulls
   in a large transitive tree (this is the specific reason Electron/npm was
   ranked below a pure-Python packaging approach for this project — see
   project memory) is itself a security cost, independent of any single
   package's own audit result.
7. **Report findings to the user** before adding the dependency: license,
   CVE scan result, maintenance signal, and transitive dependency count.
   Only add it after this is surfaced — don't silently `pip install`.

## Re-auditing existing dependencies

Periodically (and always before a release build), run
`scripts/audit_dependency.sh pip <all>` to sweep every pinned dependency in
`requirements.txt` at once via `pip-audit -r requirements.txt`.

## Additional resources

- **`scripts/audit_dependency.sh`** — runs `pip-audit`/`npm audit` for a
  single package or the whole requirements file.
