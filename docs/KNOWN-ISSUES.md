# breachsafe-ux - known issues

No open blockers at this time. New issues are tracked on the GitHub issue tracker:
https://github.com/paul007ex/breachsafe-ux/issues

## Resolved

### v0.1.0 blockers (found red-teaming the qureddy `[ui]` integration, breachsafe/qureddy#181)

All five items below are fixed in the current code and are kept here as a record.

- **W-1 descriptor dir not overridable / DESCS bound at import.** Fixed: `load_descriptors()`
  reads `BREACHSAFE_UX_TOOLS_DIR` at call time via `_tools_dir()`, and `app.build()` loads
  descriptors lazily rather than at import (`src/breachsafe_ux/facade.py`, `app.py`).
- **W-2 `main()` ignores host.** Fixed: `main()` binds
  `server_name=os.environ.get("BREACHSAFE_UX_HOST", "127.0.0.1")` (`src/breachsafe_ux/app.py`).
- **W-3 no `run.image` (Docker) backend.** Fixed: the engine dispatches
  `docker run --rm --pull=always <image> <args>` for an `image` tool source
  (`src/breachsafe_ux/facade.py`, `resolve.py`; README §6).
- **W-4 dead chain button.** Fixed: a chain button whose target tool is unavailable renders
  disabled with a "Requires `<tool>`, which is not installed" note instead of running
  (`src/breachsafe_ux/app.py`).
- **W-5 (host-side) import order.** Resolved by W-1: descriptors are discovered at call time, so a
  host sets `BREACHSAFE_UX_TOOLS_DIR` before launching without depending on import order. See
  README §2 for the environment variables.

The repository has a GitHub remote (`origin`) and CI workflows under `.github/workflows/`.
