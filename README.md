# Limatus

Limatus is a diagnose-and-steer quality loop for AI-generated content — prose today, web pages soon — built to catch generic AI slop and enforce a specific publication or product's own style rules, not just generic patterns.

## Press Release

**Anthus AI Solutions introduces Limatus, an open-source tool that tells writers exactly where AI-generated prose sounds generic — without rewriting it for them**

Teams publishing AI-assisted content face a recurring problem: drafts that are technically correct but sound like every other AI-generated draft — hedge words, empty lead-ins, uniform sentence cadence, unsupported certainty, and a voice that matches no one's actual house style. Fixing this by hand doesn't scale, and letting a model "just rewrite it" trades one set of generic patterns for another.

Limatus is a command-line tool that closes this gap in two separate steps. `limatus diagnose` reads a draft against a publication's own style profile — its voice, its lexicon, its banned phrases and patterns — and returns a structured list of findings: vague claims, empty lead-ins, uniform cadence, list-shaped prose, unsupported certainty, redundancy, and voice mismatches. It never rewrites anything; findings are signal, not verdicts. A human or agent then marks each finding skip, rewrite, delete, or keep, and only for the findings marked "rewrite" does `limatus options` generate a small set of constrained rewrite candidates — never a single mandated replacement, and never a fabricated fact, statistic, or anecdote.

"We built this because we were publishing AI-assisted content ourselves and got tired of the same tells showing up in every draft," said the Limatus team at Anthus AI Solutions. "The insight wasn't that AI writing is bad — it's that treating every publication's voice as the same generic 'professional tone' is what makes it read as AI-generated. Limatus makes house style an explicit, versioned, machine-checkable artifact instead of something an editor has to remember and enforce by hand every time."

Limatus is extracted from the editorial engine Anthus AI Solutions built and ran across dozens of real articles on its own Anth.us and Pilobolus publications, and is available today as an MIT-licensed, publication-agnostic Python package at [github.com/AnthusAI/Limatus](https://github.com/AnthusAI/Limatus).

## FAQ

**Is Limatus an AI-content detector?**
No. Limatus doesn't try to guess whether text was written by a model — it checks text against a style profile you define, regardless of who or what wrote it. It deliberately refuses to accept "detector scores" as part of a style profile; the goal is to enforce your voice, not to pass someone else's AI-detection heuristic.

**Does Limatus rewrite my content for me?**
Not automatically, and not without a human or agent explicitly opting each finding in. `limatus diagnose` only reports findings — it never touches the draft file. `limatus options` only generates rewrite *candidates* for findings you've separately marked "rewrite," and always offers more than one option so the choice of which to accept stays with an editor.

**What does a "style profile" look like?**
A YAML file naming a publication's voice, audience, tone, sentence style, structure, a preferred/avoided lexicon, evidence rules, and five to ten reference samples of real approved prose. It's the same profile used to catch drift, so it's meant to be version-controlled alongside the content it governs.

**Why is this a separate package from Papyrus?**
Papyrus is Anthus AI Solutions' own content and newsroom system, tightly coupled to Anth.us's publishing pipeline. Limatus is the general-purpose diagnose engine underneath it, extracted so any publication or product — not just Anthus's own — can adopt it without adopting the rest of Papyrus.

**What's next?**
A second capability is planned: a usability and accessibility diagnose loop for AI-generated web pages, built on Playwright and axe-core, checking WCAG 2.2 A/AA compliance across themes, viewports, and interactive states — the same diagnose-first, never-auto-fix philosophy applied to markup instead of prose.

**Is it on PyPI yet?**
Not yet — see Status below.

## Status

This package was newly extracted from Anth.us's Papyrus content system and is under active development. It is not yet on PyPI.

## Installation

```bash
pip install -e ".[dev]"
```

(PyPI installation via `pip install limatus` will be available once the package is published — see Status above.)

## Usage

```bash
limatus scan --draft path/to/draft.md --profile path/to/style-profile.yml
limatus options --draft path/to/draft.md --profile path/to/style-profile.yml \
  --diagnosis path/to/diagnosis.json --decisions path/to/decisions.json \
  --skill path/to/rewrite-skill.yml
limatus compare --profile path/to/style-profile.yml --baseline path/to/draft.md \
  --candidate path/to/candidate-a.md --candidate path/to/candidate-b.md
limatus apply --original path/to/original.md --working-copy path/to/working.md \
  --options path/to/options.json --finding-id finding-... --option-id option-... \
  --anchor "exact span text"
```

For a copy-editing agent, the intended loop is: **scan** (findings only, no steering decisions) → record **decisions** (`skip` / `rewrite` / `delete` / `keep` / `add`, via SDK or a decisions JSON file) → **options** for rewrite findings only → **compare** full-draft previews of each patch option (or regression compare after a trial edit) → **apply** exactly one human-chosen option to a working copy. Nothing auto-applies a compare winner.

Run `limatus --help` for the full command reference.

### Advisory revision verification

After a human explicitly applies a selected option to a separate working copy,
`limatus verify` compares the original and working drafts without changing,
publishing, or automatically applying either one. It reports four quality
dimensions (specificity, clarity, audience fit, and voice match), penalties for
redundancy, unsupported claims, and factual-change risk, plus evidence-backed
findings for deleted claims, duplicated ideas, residual boilerplate, and new
unsupported or factual claims.

The result includes inspectable weights: each positive quality dimension is
weighted `0.25`; redundancy is `-0.10`; unsupported claims and factual-change
risk are each `-0.20`. The default acceptance threshold is `0.05` normalized
net improvement. The recommendation is advisory and is `accept` only when
the threshold is met and the working draft has no more unsupported claims than
the original. No detector score is accepted as input or emitted in output.

## Portable style profiles

A profile is a versioned YAML or JSON document. The profile below is complete:
required fields describe the publication voice and evidence policy, while
`checks`, `rules`, and `density` make the optional controls explicit.

```yaml
schemaVersion: 1
publicationKey: example-publication
voice:
  name: Practical engineering voice
audience: Engineers evaluating tools and operational risk.
tone:
  - Conversational but precise.
sentenceStyle:
  - Prefer active voice and concrete nouns.
voicePatterns:
  - Lead with the practical stake.
structure:
  - State the claim, then its evidence and limits.
lexicon:
  prefer: [inspect, verify, latency]
  avoid: [game-changing, leverage synergies]
evidenceRules:
  - Cite primary sources and label uncertainty.
referenceSamples:
  - id: sample-one
    title: Approved sample one
    url: https://example.com/articles/one
    path: reference-samples/sample-one.md
  - id: sample-two
    title: Approved sample two
    url: https://example.com/articles/two
    path: reference-samples/sample-two.md
  - id: sample-three
    title: Approved sample three
    url: https://example.com/articles/three
    path: reference-samples/sample-three.md
  - id: sample-four
    title: Approved sample four
    url: https://example.com/articles/four
    path: reference-samples/sample-four.md
  - id: sample-five
    title: Approved sample five
    url: https://example.com/articles/five
    path: reference-samples/sample-five.md
checks:
  informationDensity: true
  uniformCadence: false
rules:
  bannedPhrases: [at the end of the day]
  bannedIntensifiers: [very]
  bannedPatterns:
    - pattern: "\\bseamless\\b"
      message: Prefer a concrete description of the integration.
  contrastCap: 2
density:
  minWords: 400
  minLexicalDensity: 0.45
  maxGzipRatio: 0.35
```

Reference `path` values are resolved relative to the profile file, not the
shell's current directory. Keep five to ten approved samples beside the
profile (or use paths such as `../samples/approved.md`). YAML and JSON use the
same field names; `features/fixtures/editorial-style-profile/portable-profile.json`
is a checked-in JSON example.

The `checks` mapping can enable or disable individual diagnose checks. If it is
omitted, every check is enabled. `rules` is optional and defaults to no custom
rules. `density` is optional and defaults to `minWords: 400`,
`minLexicalDensity: 0.45`, and `maxGzipRatio: 0.35`. Unknown control names and
invalid values fail profile validation before a draft is analyzed.

Limatus is style-focused, not an AI detector. Profile documents must not
contain detector scores or detector-related fields; the loader rejects those
keys, including nested keys.

From the repository root, run the portable fixture against a checked-in draft:

```bash
limatus diagnose \
  --draft features/fixtures/editorial-diagnosis/sloppy-draft.md \
  --profile features/fixtures/editorial-style-profile/portable-profile.json \
  --output /tmp/limatus-diagnosis.json
cat /tmp/limatus-diagnosis.json
```

The command leaves the draft unchanged and writes validated diagnostic JSON.
The same command works with a YAML profile by changing only the `--profile`
path, for example `features/fixtures/editorial-diagnosis/style-profile.yml`.

## Testing

Limatus's test suite is written in Gherkin and run with [Behave](https://behave.readthedocs.io/):

```bash
behave
```

## License

MIT — see [LICENSE](LICENSE).
