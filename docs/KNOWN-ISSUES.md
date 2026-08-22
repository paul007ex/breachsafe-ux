# breachsafe-ux - known issues


## v0.1.0 blockers (found red-teaming the qureddy `[ui]` integration, breachsafe/qureddy#181)

- **W-1 descriptor dir not overridable / DESCS bound at import.** `load_descriptors()` globs a
  hardcoded `TOOLS = ROOT/"tools"` (`src/breachsafe_ux/facade.py:14,22`) and `app.py:20` binds
  `DESCS = load_descriptors()` at import. A host package cannot point the wizard at its own
  descriptor. Fix: read `BREACHSAFE_UX_TOOLS_DIR` at call time; load DESCS lazily in `build()`.
- **W-2 `main()` ignores host.** Hardcodes `server_name="127.0.0.1"` (`app.py:224`); `BREACHSAFE_UX_HOST`
  is unread. Fix: read `BREACHSAFE_UX_HOST`.
- **W-3 no `run.image` (Docker) backend.** Portability + system-dep (OpenSSL) fix. Add dispatch:
  `docker run --rm <image@sha256> <base[1:] + args>` (strip the entrypoint tool name). Digest-pinned only.
- **W-4 dead chain button.** A `chains` button whose target tool is not installed runs and reports
  UNAVAILABLE. Fix: hide/disable a chain button when `shutil.which(target)` is None.
- **W-5 (host-side) import order.** Any host launching the wizard must set `BREACHSAFE_UX_TOOLS_DIR` before
  importing `breachsafe_ux.app` (depends on W-1). Document it.

(No GitHub remote yet; these become issues when the repo is created.)
