---
name: limatus-copy-edit-loop
description: Run Limatus diagnose-and-steer workflows on publication content—copy-edit markdown drafts against a style profile (scan, decide, options, compare, apply, headlines) and read-only HTML usability scans against a usability profile. Never auto-apply editorial patches; never modify the original draft or HTML page files.
---

# Limatus copy-edit loop

Use this skill when an agent (or human with agent assistance) copy-edits AI-assisted prose under a publication-specific style profile. Limatus reports and steers; it does not silently rewrite. The human (or an explicit human-directed apply step) chooses which option lands on disk.

Progressive disclosure: run `limatus skill` anytime to re-read this document. For prose, start with editorial **scan**; only invoke later copy-edit commands when their inputs exist. For static HTML, see **HTML usability** below (separate profile and CLI).

## Principles

- **Diagnose first.** `scan` (alias `diagnose`) is read-only on the draft file.
- **Steer explicitly.** Record `skip`, `rewrite`, `delete`, `keep`, or `add` per finding before generating options.
- **Options, not mandates.** `options` and `headline options` return multiple candidates; pick by voice and evidence, not by rank alone.
- **Compare before commit.** Use `compare` to preview full-draft effects or rank candidates; Limatus does not auto-apply the winner.
- **Working copy only.** `apply` mutates `--working-copy` only. The path passed to `--original` is read for anchoring and logging; **never edit or overwrite the original draft file.**
- **Headlines follow the profile.** When `headline.when` is `afterBody`, run title then subtitle in the order given by `headline.order`. Use each job’s YAML field key from the profile (for example `headline.title.key` and `headline.subtitle.key`), not hard-coded field names.
- **Human applies.** The agent recommends options aligned with the style profile; the human (or an explicit apply invocation they requested) runs `limatus apply` with `--finding-id`, `--option-id`, and `--anchor`.

## Workflow

1. **scan** — structured findings JSON (and optional markup outputs).
2. **decide** — append steering decisions to a decisions JSON file (one finding at a time via CLI, or batch via SDK).
3. **options** — rewrite candidates for findings marked `rewrite` only.
4. **compare** — rank `--baseline` with two or more `--candidate` previews, or regression `--original` vs `--working-copy` (read-only).
5. **apply** — write exactly one selected option into the working copy.
6. **headline options** — after body edits are on the working copy, run **title** then **subtitle** (per profile order).

Optional quality gates: **verify** (advisory, read-only), **eval** / **canary** for corpus regression manifests.

## Commands

Examples use `python -m limatus`; the installed `limatus` entry point is equivalent.

### scan

```bash
python -m limatus scan \
  --draft path/to/draft.md \
  --profile path/to/style-profile.yml \
  --output path/to/diagnosis.json
```

### decide

```bash
python -m limatus decide \
  --finding-id finding-0123456789abcdef \
  --decision rewrite \
  --note "needs concrete options" \
  --decisions path/to/decisions.json
```

### options

```bash
python -m limatus options \
  --draft path/to/draft.md \
  --profile path/to/style-profile.yml \
  --diagnosis path/to/diagnosis.json \
  --decisions path/to/decisions.json \
  --skill path/to/editorial-rewrite-skill.yml \
  --output path/to/options.json
```

### compare

Rank mode (at least two candidates):

```bash
python -m limatus compare \
  --profile path/to/style-profile.yml \
  --baseline path/to/draft.md \
  --candidate path/to/candidate-a.md \
  --candidate path/to/candidate-b.md
```

Regression mode (read-only paths):

```bash
python -m limatus compare \
  --profile path/to/style-profile.yml \
  --original path/to/original.md \
  --working-copy path/to/working.md
```

### apply

```bash
python -m limatus apply \
  --original path/to/original.md \
  --working-copy path/to/working.md \
  --options path/to/options.json \
  --finding-id finding-0123456789abcdef \
  --option-id option-0123456789abcdef \
  --anchor "exact span text from the draft"
```

Only `--working-copy` is modified. Treat `--original` as immutable.

### headline options

Run after body work, in profile order (typically title, then subtitle):

```bash
python -m limatus headline options \
  --job title \
  --working-copy path/to/working.md \
  --profile path/to/style-profile.yml \
  --skill path/to/editorial-rewrite-skill.yml

python -m limatus headline options \
  --job subtitle \
  --working-copy path/to/working.md \
  --profile path/to/style-profile.yml \
  --skill path/to/editorial-rewrite-skill.yml
```

Map `--job title|subtitle` to the profile’s `headline.<job>.key` when editing front matter.

### eval and canary

```bash
python -m limatus eval --manifest path/to/editorial-corpus/manifest.yml
python -m limatus canary --manifest path/to/editorial-canary/manifest.yml
```

## HTML usability

Use this path for static HTML pages (landing pages, articles rendered to HTML)—not for markdown copy-edit drafts. It is **read-only**: Limatus reports findings; it does not rewrite the page. There is no `usability options`, `usability apply`, or other usability write commands.

The profile is a **usability profile** (thresholds for contrast, tap targets, focus visibility, etc.). It is **not** the editorial `style-profile.yml` used by `scan` / `options` / `apply`.

```bash
python -m limatus usability scan --page FILE.html --profile FILE.yml [--output findings.json]
```

Structured finding kinds include:

- `missing_alt`
- `low_contrast`
- `small_tap_target`
- `suppressed_focus_outline`
- `missing_accessible_name`
- `missing_lang`
- `emoji_heading`
- `generic_gradient_hero`

Route usability findings to human or design-system fixes outside the editorial decide/options/apply loop.

## Agent steering

- Read the style profile (voice, lexicon, evidence rules, reference samples) before deciding.
- Prefer options that fix the finding without inventing facts, statistics, or anecdotes.
- Do not auto-run `apply` or treat compare output as permission to write files.
- Do not pick an `--option-id` on behalf of the human unless they explicitly asked you to run `apply` with that id and anchor.
