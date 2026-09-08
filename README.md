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
limatus diagnose --draft path/to/draft.md --profile path/to/style-profile.yml
limatus options --draft path/to/draft.md --profile path/to/style-profile.yml \
  --diagnosis path/to/diagnosis.json --decisions path/to/decisions.json \
  --skill path/to/rewrite-skill.yml
```

Run `limatus --help` for the full command reference.

## Testing

Limatus's test suite is written in Gherkin and run with [Behave](https://behave.readthedocs.io/):

```bash
behave
```

## License

MIT — see [LICENSE](LICENSE).
