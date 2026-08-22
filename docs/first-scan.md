<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Your first scan (and how to read the verdict)

A five-minute walkthrough: launch EnXemble, run a Harvest-Now-Decrypt-Later (HNDL) audit against
a public endpoint, and read the result correctly. No configuration required.

## 1. Launch

```bash
docker rm -f $(docker ps -aq --filter publish=7860) 2>/dev/null   # clear any previous run on :7860
docker run -d --pull=always -p 7860:7860 --name enxemble ghcr.io/paul007ex/qureddy-ux:latest
sleep 10 && open http://localhost:7860       # macOS  ·  Linux: xdg-open  ·  Windows: start
```

Your browser opens on the host. It is self-contained (the QuReddy scanner + openssl are inside
the image), so there is nothing else to install.

## 2. Run the scan

1. You land on the **HNDL Audit (TLS)** tab. The **host** field is already filled with a public
   post-quantum test endpoint, so you can scan immediately.
2. Click **HNDL Audit (TLS)**. The scan connects to the endpoint, inspects its TLS key exchange,
   and produces a CycloneDX 1.7 CBOM (cryptography bill of materials).
3. To scan your own endpoint, replace the host (e.g. `example.com:443`) and click again. The
   **HNDL Audit (SSH)** tab does the same for an SSH endpoint.

## 3. Read the verdict — the three-state badge

The badge is the point of the tool. It reports the result of an **external validator**, never a
guess, and it has exactly three states:

| Badge | What it means | What it does NOT mean |
|---|---|---|
| **VALID** | The validator ran and accepted the artifact. | — |
| **INVALID** | The validator ran and rejected the artifact. | Not "the scan crashed." |
| **VALIDATOR-UNAVAILABLE** | The tool or validator could not run (missing dependency, Docker down, timeout, empty output). | **Never** a pass in disguise. |

The rule that matters: a crashed scan, a missing validator, or an empty run resolve to
**VALIDATOR-UNAVAILABLE** — they are never shown as VALID. Colour is only a redundant cue; the
word carries the state. If you see green, a real validator really accepted a real artifact.

Below the badge, the **posture** summary explains the finding in plain terms (for example, an
endpoint offering only classical key exchange is flagged as a present-day harvest-now,
decrypt-later confidentiality risk), and the raw tool output is shown for inspection.

## 4. Where the artifact goes

Each run writes to a unique per-run directory under `~/mint-proof/wizard-runs` (override with
`BREACHSAFE_UX_RUN_ROOT`). The CBOM/JSON artifact there is what the validator reads to derive
the badge, and what you can archive or feed downstream (for example into Qurum).

## 5. Verify the environment

To confirm every tab's tool and validator resolve before you rely on a result:

```bash
docker exec enxemble breachsafe-ux --check     # exit != 0 if any tool/validator is missing
```

This prints, per tab, the exact binary, version, and path in use (scanner, validator, and the
connection tool) — the same provenance shown greyed-out inside each tab's **Advanced** section.

## Next steps

- Add your own tool as a one-file YAML descriptor: see [`../README.md`](../README.md) §5 and
  [`descriptor-tokens.md`](descriptor-tokens.md).
- Understand the host/descriptor boundary: [`adr/0002-host-descriptor-boundary.md`](adr/0002-host-descriptor-boundary.md).
