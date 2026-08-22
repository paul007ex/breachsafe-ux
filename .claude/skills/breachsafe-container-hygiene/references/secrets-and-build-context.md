# Secret-leak / .dockerignore / build-context hygiene

## Contents
1. No secret in an image layer
2. .dockerignore (deny-all model)
3. Tight build context

## 1. No secret in an image layer
No credential in `ENV`, in `ARG` (visible in `docker history`), or via a `COPY`'d `.env`. A layer is permanent even if a later layer deletes the file. Use BuildKit `RUN --mount=type=secret,id=…` for build-time secrets — they never land in a layer. A real secret found here escalates to `breachsafe-security-audit`.

## 2. .dockerignore (deny-all model)
Exclude secrets, VCS, cruft, and **test code**. EnXemble's root `.dockerignore` is the model: deny-all (`*`) then re-include exactly the COPY sources, with belt-and-suspenders `**/tests` / `**/.env*` / `**/.git` globs (#133/#137, "never ship TEST code"). Deny-all is safer than an allow-list — a new secret file is excluded by default.

## 3. Tight build context
A huge repo root as context is slow to send to the daemon and leak-prone (any file in context can be `COPY`'d). The deny-all `.dockerignore` narrows it; prefer a scoped context dir where practical.

Sources: Docker `.dockerignore` + build-context best-practices (https://docs.docker.com/build/building/best-practices/).
