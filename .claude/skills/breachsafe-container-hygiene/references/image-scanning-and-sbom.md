# Image scanning (Trivy/Grype) + SBOM

## Contents
1. Scan for OS + language CVEs
2. The scanner must FAIL the build
3. .trivyignore discipline
4. SBOM + the generator→consumer pitfall

## 1. Scan for OS + language CVEs
Scan the built image (not just the source tree) with Trivy or Grype — it resolves the OS package DB + language lockfiles inside the image. BreachSAFE ships a reusable Trivy composite action (`.github/actions/trivy-scan/action.yml`) with SARIF upload to code-scanning.

## 2. The scanner must FAIL the build
A scan that reports but never gates is theater (same trap `breachsafe-release` names for `cargo audit`). Flag: BreachSAFE's `trivy-scan` action defaults `fail-on-critical: 'false'`. Check the CI **exit path** — does a CRITICAL return non-zero and block merge/publish? — not merely that the tool ran.

## 3. .trivyignore discipline
Every suppression scoped per-package with: (a) why-it-ships, (b) why-not-exploitable, (c) upstream-fix-status, (d) an `exp:` expiry date. EnXemble's `.trivyignore` is the model (all four per entry). A bare `CVE-XXXX` with no rationale/expiry is a finding — an indefinite blind spot.

## 4. SBOM + the generator→consumer pitfall
Emit CycloneDX (security) or SPDX (license) via Syft, or buildx `--sbom=true` (qureddy `container.yml`). Pitfall: a Syft SBOM that Trivy/Grype then fails to parse yields a silent **"0 vulns"** — a false all-clear. Test the specific generator→scanner pairing on a known-vulnerable image; don't trust an empty result.

Sources: Trivy (https://trivy.dev/), Syft/Grype (https://github.com/anchore/syft, https://github.com/anchore/grype).
