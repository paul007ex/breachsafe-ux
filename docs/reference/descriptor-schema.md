<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Descriptor schema

The complete field contract for a tool descriptor. One tool is one YAML file at
`tools/<id>/<id>.yaml`. The authoritative machine-readable schema is
[`src/breachsafe_ux/descriptor.schema.json`](../../src/breachsafe_ux/descriptor.schema.json)
(JSON Schema 2020-12); this page is the human reference. For a worked walkthrough see
[add a tool](../how-to/add-a-tool.md); for the argv tokens see
[descriptor tokens](descriptor-tokens.md).

Required top-level keys: `id` and `run`. No unknown keys are allowed.

## Top-level fields

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Slug matching `^[a-z0-9][a-z0-9-]*$`; must equal the `tools/<id>/<id>.yaml` directory and file name. |
| `run` | object | How the tool is executed. See [run](#run). |
| `schema_version` | integer | Descriptor schema version. Absent is treated as `1`. |
| `order` | integer | Tab sort order (lower first). |
| `standalone` | boolean | `false` = chain-only: reached via another tool's chain button, no tab of its own. |
| `feature_flag` | string | Gate the descriptor behind `BREACHSAFE_UX_<FLAG>` (default on). See [enable optional tabs](../how-to/enable-optional-tabs.md). |
| `title` | string | Tab title. |
| `run_label` | string | Run-button label. Absent = `Run <id>`. |
| `description` | string | Shown under the title. |
| `brand` | object | Display-only header/footer metadata. See [brand](#brand). |
| `inputs` | array | Form fields. See [inputs](#inputs). |
| `validate` | object | External validator. See [validate](#validate). |
| `render` | object | How the result is displayed. See [render](#render). |
| `actions` | array | Descriptor-declared buttons. See [actions](#actions). |
| `chains` | array | Hand-off buttons to another descriptor. See [chains](#chains). |

## inputs

Each input is a form field and maps to argv by **at most one** of `positional`, `arg`, or
`flag`. An input with none is a token-only value referenced as `{name}` in `run.positional_from`,
`run.argv`, or `validate.argv`.

| Field | Type | Meaning |
|---|---|---|
| `name` | string | Field name; the `{name}` token. Required. |
| `type` | enum | `text`, `int`, `float`, `bool`, `enum`, or `file`. Required. |
| `label` | string | Field label. |
| `placeholder` | string | Placeholder text. |
| `info` | string | Help text under the field. |
| `required` | boolean | Whether the field must be set. |
| `default` | any | Default value. |
| `min` / `max` | number | Bounds for numeric inputs. |
| `widget` | enum | `slider` to render a numeric input as a slider. |
| `choices` | array | Allowed values; required when `type: enum`. |
| `group` | enum | `advanced` to place the field behind a collapsible section. |
| `arg` | string | Emit `[--x, value]` when set. |
| `flag` | string | Emit `--x` only when the value is truthy. |
| `positional` | boolean | Emit the value as a positional argument. |
| `verify_argv` | array | argv for a per-field "Verify" button (uses `{value}`). |
| `accept` | array | For `type: file`, accepted extensions. |

`arg`, `flag`, and `positional` are mutually exclusive. An `enum` input must declare `choices`.

## run

Exactly one of `base` or `argv`.

| Field | Type | Meaning |
|---|---|---|
| `base` | array | Fixed command prefix, e.g. `[gitleaks, detect]`; options and positionals are appended. |
| `argv` | array | Fully static argv (no input-driven assembly), with tokens. |
| `positional_from` | string | Compose one positional from a template, e.g. `{host}:{port}`. |
| `artifact_from` | enum | `stdout` to use captured stdout as the artifact; omit if the tool writes the artifact file itself. |
| `artifact_name` | string | The artifact's file name. |
| `image` | string | Docker image whose entrypoint is the tool; used as a fallback when the binary is not on `PATH`. Pin by `@sha256`. |
| `timeout_s` | integer | Run timeout in seconds. |
| `trust_artifact_on_nonzero` | boolean | Allow a nonzero exit to still badge from the artifact (default: nonzero → unavailable). |
| `no_end_of_options` | boolean | Opt out of the `--` end-of-options guard (weaker posture). |

The host emits all options first, then a literal `--`, then positionals, so a leading-dash value
can never be parsed as a flag. See [execution backends](execution-backends.md).

## validate

Either a single validator (`argv` + `badge_rule`) **or** one selected by an input value
(`by` + `cases`). These two forms are mutually exclusive.

| Field | Type | Meaning |
|---|---|---|
| `argv` | array | Validator argv (single-validator form), with tokens. |
| `badge_rule` | object | Maps validator output to a badge state (single-validator form). See [badge rule](#badge_rule). |
| `by` | array | Input name(s) that select the validator; multi-key values are joined with `\|`. |
| `cases` | object | Keyed by the joined `by` values; each value is a validator case or `null` (explicit "no validator" → badge `none`). |
| `default` | object/null | Used when no case matches; `null` or absent = no validator. |
| `timeout_s` | integer | Validator timeout in seconds. |

A validator case (under `cases` / `default`) has `argv` + `badge_rule`, and optional `timeout_s`.
**Fail-closed:** a variant with no validator badges `none`, never a green.

### badge_rule

Maps validator output to a state. An empty or unknown condition never passes.

| Field | Type | Meaning |
|---|---|---|
| `pass_if` | condition | When met, badge `VALID`. |
| `fail_if` | condition | When met, badge `INVALID`. |
| `unavailable_if` | condition | When met, badge `VALIDATOR-UNAVAILABLE`. |
| `otherwise` | enum | Fallback state: `valid`, `invalid`, `unavailable`, or `none`. |
| `fail_detail_grep` | string | Pattern to surface a failure detail. |

A condition is an AND of any of `exit` (integer), `stdout_contains`, `stdout_contains_any`
(array), and `stdout_not_contains`. An empty condition is rejected (fail-closed). See
[the three-state verdict](../explanation/three-state-verdict.md) and [badge](badge.md).

## render

| Field | Type | Meaning |
|---|---|---|
| `primary` | enum | `json` to render the artifact as JSON. |
| `highlights` | array | `{ label, find_prop }` values pulled from the artifact. |
| `posture` | object | A finding banner derived from the artifact (`from` + `cases` + optional `default`), decoupled from the badge. Each case is `{ text, level }` with level `high`/`medium`/`ok`/`unknown`. |
| `badge_text` | object | Per-state headline override so a green badge states what was checked rather than implying a verdict. Keys: `valid`/`invalid`/`unavailable`/`none`. |

The host never computes a domain verdict; `posture` only maps a value it reads from the artifact.

## actions

A descriptor-declared button that runs its own argv against the current inputs and shows
OK/FAIL (for example a connection test).

| Field | Type | Meaning |
|---|---|---|
| `label` | string | Button text. Required. |
| `argv` | array | Action argv (same token namespace as `run.argv`; stdin is closed). Required. |
| `ok_if` | condition | When met, the action shows OK. |
| `timeout_s` | integer | Action timeout in seconds. |

## chains

Hand this tool's artifact to another descriptor via a button.

| Field | Type | Meaning |
|---|---|---|
| `to` | string | Target descriptor `id`. Required. |
| `label` | string | Button text. |
| `pass_artifact_as` | string | The target input name the artifact is passed as. |
| `with` | object | Extra input values to preset on the target. |
| `feature_flag` | string | Gate the button behind `BREACHSAFE_UX_<FLAG>` (default on). |

## brand

Display-only header/footer metadata. String values may reference environment variables (for
example `${SOME_VERSION}`), expanded before render and never used in run/validate argv.

| Field | Type | Meaning |
|---|---|---|
| `product` | string | Product name shown in the tab header. |
| `version` | string | Fallback version string. |
| `version_cmd` | array | Command run to derive the shown version from the installed tool. |
| `url` | string | Product URL. |
| `repo` | string | Repository URL. |
