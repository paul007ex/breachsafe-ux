<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Threat model — EnXemble UX host

[`threagile.yaml`](threagile.yaml) is a [Threagile](https://threagile.io) (agile
threat-modeling) model of the EnXemble UX host (breachsafe-ux / qureddy-ux). It encodes the
trust-boundary reasoning that already lives in prose in
[`ADR-0002`](../docs/adr/0002-host-descriptor-boundary.md) (host ↔ descriptor boundary,
operator-owned exposure, no in-image auth) and
[`ADR-0003`](../docs/adr/0003-docker-packaging.md) (self-contained tool image, `run.image`
docker fallback), so the design's security posture is checkable in CI. Part of #110.

## What the model captures

- **Data assets:** tool descriptors, scan artifacts / CBOM, subprocess argv.
- **Technical assets:** the Gradio host, the no-shell subprocess tool runner, the external
  validator, and the optional `run.image` docker backend (plus the external operator, scanned
  endpoint, and pulled tool image).
- **Trust boundaries:** operator ↔ host (the operator-owned exposure boundary — `-p` mapping /
  reverse proxy / VPN, loopback by default), the host runtime (container) execution environment,
  and the tool-image sandbox (host ↔ tool image).
- **Mitigations already in place:** no-shell argv exec, the end-of-options `--` guard, the
  fail-closed 3-state badge, and the operator-boundary trust posture. These appear as
  communication-link properties, `abuse_cases`, `security_requirements`, and asset descriptions.
- **Accepted risks:** the operator-boundary "no in-image authentication" decision (ADR-0002 §3,
  #7/#22 wontfix) is recorded in `risk_tracking` as `accepted`, so it does not read as an
  unhandled risk.

## Regenerating / validating locally

Threagile is run from its official container image, pinned by digest (v1.0.0). Update the digest
deliberately — it is set in both this command and
[`.github/workflows/threagile.yml`](../.github/workflows/threagile.yml).

```bash
IMG=threagile/threagile@sha256:abb9eccb111a2059c4876759a24245db02ad295b1608d3a4634ec250f38d9640

# Validate the model and generate risks.json (+ report, diagrams) into ./threagile-out
mkdir -p threagile-out
docker run --rm \
  -v "$PWD/threat-model:/model:ro" \
  -v "$PWD/threagile-out:/out" \
  "$IMG" -model /model/threagile.yaml -output /out

# Apply the same gate CI uses (fails on HIGH/CRITICAL unmitigated risks)
python3 scripts/threagile_gate.py threagile-out/risks.json
```

Threagile validates the model as part of the run: it exits non-zero on a schema/parse error or on
orphaned `risk_tracking` IDs. Enum values are listed by
`docker run --rm "$IMG" -list-types`; a fresh stub is `-create-stub-model`.

## The CI gate

[`.github/workflows/threagile.yml`](../.github/workflows/threagile.yml) runs on PRs that touch
`threat-model/**` (SHA-pinned actions, `contents: read`, concurrency-guarded). It runs Threagile
in the digest-pinned container and then runs
[`scripts/threagile_gate.py`](../scripts/threagile_gate.py), which **fails the build on any
`high`/`critical` risk whose `risk_status` is `unchecked` or `in-discussion`**. Risks tracked as
`accepted` / `mitigated` / `in-progress` / `false-positive` pass. The current model generates no
high/critical risks, so the gate is green.

## Re-seeding `risk_tracking` after a model change

Threagile risk IDs (`synthetic_id`) encode the names of the assets and links involved, so renaming
an asset or link changes the ID and can orphan a `risk_tracking` entry (Threagile then exits
non-zero). After such a change, re-read the IDs from a local run and update `risk_tracking`:

```bash
python3 -c "import json;[print(r['severity'],r['risk_status'],r['synthetic_id']) for r in json.load(open('threagile-out/risks.json'))]"
```
