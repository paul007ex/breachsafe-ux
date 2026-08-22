---
name: breachsafe-ux-frameworks
description: Choose and architect a UX across specific frontend/tool-UI frameworks — Gradio/Streamlit (Python), script-server/Wooey (CLI-wrappers), Next.js/React (product-grade), and low-code platforms (Windmill/Tooljet/Appsmith) — plus the UX-architecture decisions that sit above them (universal facade vs bespoke-per-tool vs layered; config-driven vs code; design-token/white-label theming; borrow-the-schema-not-the-component). Use when picking a UI framework, designing a generic tool-facade, or deciding how a tool surface should be built and branded. Distinct from breachsafe-prowler-ux (work WITHIN the existing EnXemble Next.js app "as if Prowler built it") — this skill chooses BETWEEN frameworks and designs the UX architecture. Pairs with breachsafe-build-vs-buy (the acquisition archetype) and breachsafe-oss-eval (scoring one candidate). Design/decision only.
---

# breachsafe-ux-frameworks

Answers: **"what UI framework, and what UX architecture, for this surface — and can we
brand it and ship it?"** UX frameworks are *special*: a UI component is usually welded to its
stack, licenses vary wildly, and "config-driven vs code" changes the whole cost curve. Treat
the framework choice as an architecture decision, not a preference.

## Contents
1. Stay in its lane
2. Authorization gate
3. Why UX frameworks are special (the non-obvious traps)
4. The UX-architecture decision: universal vs per-tool vs layered
5. Framework tradeoff map
6. Theming / white-label (design tokens)
7. UX-quality checklist (Nielsen)
8. Deliverable

## 1. Stay in its lane

- **`breachsafe-prowler-ux`** = change the *existing* EnXemble Next.js/DRF app idiomatically.
  This skill = choosing *which* framework and designing the UX architecture (often for a NEW
  surface like a tool-facade).
- **`breachsafe-build-vs-buy`** owns the acquisition archetype (build/fork/adopt/platform);
  **`breachsafe-oss-eval`** scores one candidate. This skill supplies the UX-specific criteria
  they weigh.
- **`breachsafe-architecture-review`** owns backend/system design.

## 2. Authorization gate

Design + recommendation only. Prototype read-only in the study area; never ship a UI, take a
framework dependency, or commit a surface without explicit authorization.

## 3. Why UX frameworks are special (the non-obvious traps)

1. **Coupling: borrow the schema, never the component.** A form/component is welded to its
   stack (server actions, design system, router, state lib). Lifting a `.tsx` drags the whole
   app; the reusable asset is the **schema/contract** (zod/JSON-schema) behind it. (Verified
   precedent: EnXemble's `endpoint-scan-form.tsx` is glued to `@/actions/*` + shadcn +
   react-hook-form; only `endpoint-target.ts` is portable.)
2. **License decides shippability.** For a foundation you SHIP AND SELL, you need **permissive
   (MIT / Apache-2.0 / BSD)**. **AGPL** (Windmill core, Tooljet) forces open-sourcing your
   product or a commercial license; **Elastic/BSL** restrict resale. This can eliminate an
   otherwise-great framework before UX even matters — check the LICENSE first. (Your product
   code may be PolyForm-Noncommercial, but the framework *under* it must be permissive to sell.)
3. **Config-driven vs code is the cost curve.** "Add a tool by config" (script-server) scales
   to N tools cheaply; "code per tool" (Gradio/Streamlit) is fast for 1-2, linear after.
4. **Time-to-pretty vs control.** Python UI libs give a pretty demo in ~30 LOC but cap on
   layout/branding/multi-tenant; product-grade (Next.js/React) is slow to start, no ceiling.
5. **Honesty carries into the UI.** A validation/status badge must reflect the *real* external
   validator, never a green the tool self-reported (the false-green rule from
   `breachsafe-quality-review`).

## 4. The UX-architecture decision: universal vs per-tool vs layered

| Pattern | When | Cost |
|---|---|---|
| **1 universal facade** | many tools sharing `input → run → validate → output` | cheap breadth; generic look |
| **1 bespoke UX per tool** | a domain that needs tailored interaction | rich; N× build cost |
| **Layered (recommend)** | universal facade for breadth **+** bespoke only for the flagship depth flow | best of both |

**Rule: breadth → universal facade · depth → bespoke, sparingly · share the schema, never the
component.** (E.g. qureddy/mint-oscal/quorum → the universal facade; EnXemble endpoint-scanning
stays its own rich UX; both derive from the same shared contracts.)

## 5. Framework tradeoff map

| Framework | Add-a-tool | License (ship&sell?) | Theming | Best for |
|---|---|---|---|---|
| **script-server** | **config-only** | Apache-2.0 ✅ | thin | generic multi-CLI console, fast |
| **Wooey** (Django) | argparse-auto | BSD ✅ | thin | Python-argparse tools, DB/users |
| **Gradio** | code per tool | Apache-2.0 ✅ | medium | pretty per-tool demo/MVP |
| **Streamlit** | code per tool | Apache-2.0 ✅ | medium | data dashboards |
| **Next.js/React** | code (product) | MIT ✅ | full/white-label | shipped product surface (EnXemble) |
| **Appsmith** | drag-drop | Apache-2.0 ✅ | medium | internal tools, multi-user |
| **Windmill** | typed-fn→auto-UI | **AGPL** ⚠️ (commercial reqd to sell closed) | medium | scripts→apps platform |
| **Tooljet** | drag-drop | **AGPL** ⚠️ | medium | internal-tool platform |

Verify the license line against the repo's actual LICENSE each time — they change.

## 6. Theming / white-label (design tokens)

- Drive branding from a **single source of truth** (a token layer), not N literals — mirror
  EnXemble's `ui/config/brand.ts` (name lockup, company/product, AI name, tagline) +
  `ui/styles/globals.css` design tokens (e.g. `--color-bs-cyan-*`).
- For a facade meant for others, brand = a swappable descriptor (logo, primary color, name),
  so BreachSAFE ships branded and a third party rebrands by config, not a fork.

## 7. UX-quality checklist (Nielsen's 10 heuristics)

Score any surface against: visibility of system status (live run/validate feedback), match to
the real world, user control/undo, consistency, error prevention, recognition over recall,
flexibility, minimalist design, help users recover from errors (honest messages, not
tracebacks), help/docs. Weight *status visibility* and *error recovery* highest for a
run-a-tool facade.

## 8. Deliverable

A framework recommendation (with the license-to-ship check explicit), the UX architecture
(universal / per-tool / layered + what's shared), the theming/token plan, and a Nielsen pass
on the proposed surface. Feed the framework criteria into `breachsafe-build-vs-buy`'s matrix
rather than duplicating the acquisition decision here.
