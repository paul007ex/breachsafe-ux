# Signing + attestation (cosign / SLSA)

## Contents
1. Sign by digest, keyless
2. Verify with a pinned identity
3. Provenance + SBOM attestations
4. Defers to breachsafe-release

## 1. Sign by digest, keyless
`cosign sign <img>@sha256:…` — sign the **digest**, never a mutable tag. Prefer **keyless** via GitHub Actions OIDC (Fulcio short-lived cert + Rekor transparency log) over long-lived keys. `cosign sign` writes to a public log — effectively irreversible, so it needs explicit authorization.

## 2. Verify with a pinned identity
```
cosign verify <img>@sha256:… \
  --certificate-identity-regexp 'https://github.com/<org>/<repo>/.*' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```
Verifying without pinning identity + issuer accepts *any* valid Sigstore signature — useless. The identity regexp ties the signature to *your* workflow.

## 3. Provenance + SBOM attestations
buildx `--provenance=true --sbom=true` emits SLSA provenance + an SBOM attestation. Verify: `cosign verify-attestation --type slsaprovenance` / `--type cyclonedx`. Gap: qureddy's publish sets `--provenance=true --sbom=true` but **no repo runs `cosign` at all** — nothing is signed or signature-verified. `--provenance=true` is metadata, not a verified signature.

## 4. Defers to breachsafe-release
`breachsafe-release` is the canonical authority on the Sigstore/SLSA framing and the "is the package release-ready" verdict. This file is the image-artifact mechanics only.

Sources: Sigstore cosign (https://docs.sigstore.dev/cosign/verifying/verify/), SLSA (https://slsa.dev/).
