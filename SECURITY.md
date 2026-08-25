<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Security Policy

[![SPDX: reuse](https://img.shields.io/badge/license%20headers-reuse-green?style=flat-square)](https://reuse.software/)
[![Disclosure SLA](https://img.shields.io/badge/disclosure%20SLA-5%20business%20days-brightgreen?style=flat-square)](#3-response-targets)

BreachSAFE EnXemble is a web-facing tool. We take vulnerability reports seriously.

## Contents

1. [Supported versions](#1-supported-versions)
2. [Report a vulnerability](#2-report-a-vulnerability)
3. [Response targets](#3-response-targets)
4. [Disclosure policy](#4-disclosure-policy)
5. [Scope](#5-scope)
6. [Security exceptions](#6-security-exceptions)

## 1. Supported Versions

| Version | Supported |
|---|---|
| `main` (development) | Yes |
| Latest published `0.13.x` | Yes |
| `0.12.x` and earlier | No |

Security fixes target `main` and the latest published minor release. No
backport commitment exists for earlier versions.

## 2. Report a vulnerability

**Do not file a public GitHub issue for vulnerabilities.**

Use **GitHub Security Advisories** at
https://github.com/breachsafe/breachsafe-enxemble/security/advisories/new to report
privately. The repository maintainer is automatically notified.

If you cannot use GitHub Security Advisories, email the maintainer; the contact
is maintained through the BreachSAFE GitHub organization.

### What to include

- A description of the vulnerability and its impact
- Reproduction steps or proof-of-concept
- The version (commit SHA or release tag) you tested against
- Your contact info for follow-up

## 3. Response targets

We commit to:

- **Acknowledgement within 5 business days** of receipt
- **Initial assessment within 10 business days** (severity classification, fix planning)
- **Fix or disclosure timeline within 30 business days** for critical and high severity
- **Coordinated disclosure** at a date you and the maintainer agree on

If we miss any of these, you are entitled to escalate by re-opening the report
or going public with the details and disclosure timeline.

## 4. Disclosure Policy

We follow **coordinated disclosure**:

1. Reporter sends a private report.
2. Maintainer acknowledges, classifies, and proposes a fix and disclosure date.
3. Both parties agree on timing.
4. Fix is developed in a private fork.
5. On the agreed date, the fix is published, a GitHub Security Advisory is posted
   with CVE assignment if eligible, and the reporter is credited (unless they
   request otherwise).

We will not retaliate against reporters acting in good faith. We will not pursue
legal action against researchers who follow this disclosure policy.

## 5. Scope

In scope:

- The breachsafe-ux web application and Python package (`breachsafe-ux`)
- The tool descriptors and the way the host renders, runs, and reports them
- Distributed artifacts (wheel, source distribution, and Docker images when published)
- Documentation that misleads users about a verdict or a security posture

Out of scope:

- Vulnerabilities in dependencies that have been disclosed and patched upstream;
  file with the upstream project
- Vulnerabilities in the wrapped tools themselves; report those to the tool's project
- Theoretical issues without a working PoC
- Social engineering of contributors
- Denial of service against the breachsafe-ux maintainers

## 6. Security Exceptions

Time-bounded security exceptions are documented in the pull request that
introduces them. Format:

```
SECURITY EXCEPTION ACCEPTED: <rule>, because <reason>, expires <date or issue link>
```

No exception exists until it is recorded and reviewed in the pull request that
introduces it. Permanent silent exceptions do not exist.
