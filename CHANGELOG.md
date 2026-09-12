# CHANGELOG


## v0.22.0 (2026-09-12)

### Chores

- **kanbus**: Commit board state (issues)
  ([`95cecb0`](https://github.com/AnthusAI/Limatus/commit/95cecb0ffec320a7e134d0f69e969a2d853351aa))

### Features

- **usability**: Add small tap target scan (LIM-17723e)
  ([#32](https://github.com/AnthusAI/Limatus/pull/32),
  [`a4375e2`](https://github.com/AnthusAI/Limatus/commit/a4375e29dc8d873e6a9c3a991cb9af028f91310e))

Extend usability scan with small_tap_target findings, tapTarget.minPx profile default, and
  deterministic width/height resolution from attrs, inline styles, and embedded CSS rules.


## v0.21.0 (2026-09-12)

### Chores

- **kanbus**: Commit board state (issues)
  ([`995a263`](https://github.com/AnthusAI/Limatus/commit/995a263de7a3e16b8fbaeb7cd99363d67ffe547c))

- **kanbus**: Commit board state (issues)
  ([`aaea8b7`](https://github.com/AnthusAI/Limatus/commit/aaea8b7a32ff79ccb82013f2fb3fd4d97a9a4165))

- **kanbus**: Commit board state (issues)
  ([`3287c46`](https://github.com/AnthusAI/Limatus/commit/3287c46b310067e5d515d55118c768e4591f18ad))

### Features

- **usability**: Read-only HTML scan (LIM-274a81)
  ([#31](https://github.com/AnthusAI/Limatus/pull/31),
  [`0a2f37d`](https://github.com/AnthusAI/Limatus/commit/0a2f37decbb91cfc225026912788527f4024e761))

* feat(usability): add read-only HTML scan for LIM-274a81

Introduce `limatus usability scan` with a dedicated usability profile schema, WCAG contrast checks,
  and missing-alt detection without touching editorial scan output.

* fix(usability): void HTML elements and test hygiene (LIM-274a81)

Pop void tags off the parser stack so siblings are not nested under img, harden 3-digit hex parsing,
  and use temp dirs for CLI/profile tests plus a read-only page byte check.


## v0.20.0 (2026-09-11)

### Chores

- **kanbus**: Close rewrite-loop epic; start LIM-3863ed skill CLI
  ([`5bca7dd`](https://github.com/AnthusAI/Limatus/commit/5bca7dd29318258d79ec5e7540e47cc106233dde))

### Features

- **cli**: Print packaged SKILL.md via limatus skill
  ([#30](https://github.com/AnthusAI/Limatus/pull/30),
  [`6c60b3d`](https://github.com/AnthusAI/Limatus/commit/6c60b3d8406bde1fb8a87e875291b945e542cc25))

LIM-3863ed — Package copy-edit Agent Skill in the wheel and expose it through a
  progressive-disclosure `limatus skill` subcommand.


## v0.19.0 (2026-09-11)

### Chores

- **kanbus**: Close LIM-fc61e8; start preferredPhrasing LIM-74d5fb
  ([`31fe252`](https://github.com/AnthusAI/Limatus/commit/31fe252b8e41fcb161728f95fabfd55cb6e09192))

### Features

- **style**: Preferredphrasing from/to profile reword hints
  ([#29](https://github.com/AnthusAI/Limatus/pull/29),
  [`a498f22`](https://github.com/AnthusAI/Limatus/commit/a498f22660910dc946d738e4637412534017a840))


## v0.18.0 (2026-09-11)

### Chores

- **kanbus**: Close evals epic (#28); start LIM-fc61e8 voice audit
  ([`de4633a`](https://github.com/AnthusAI/Limatus/commit/de4633aba2cb87cb2cfb08d91ac2106072532ab0))

- **kanbus**: Close false HITL wait; start Papyrus SDK adapter
  ([`2cf8b30`](https://github.com/AnthusAI/Limatus/commit/2cf8b302918dbc2599cc35cb1758bfc5b51d085f))

LIM-80209b was parked on a stale Ryan-option-id gate. LIM-3ff8d0 / LIM-209793 in progress.

- **kanbus**: Close LIM-3ff8d0 Papyrus SDK integration
  ([`60c3d81`](https://github.com/AnthusAI/Limatus/commit/60c3d81d0ef27234a51e2d914c21d553bf4d11de))

Papyrus #80 landed on develop. LIM-209793 and the epic are done.

- **kanbus**: Close LIM-81ecb1 (#27); start LIM-658c60 metrics
  ([`25e7a07`](https://github.com/AnthusAI/Limatus/commit/25e7a0723edd4859e3ae7e98f1eaa91d4ae5db97))

- **kanbus**: Lim-fc61e8 Chatticus covered; Anth.us PPY-cc58ab
  ([`18e864f`](https://github.com/AnthusAI/Limatus/commit/18e864f6d49390db8d43a999468f94b7aa33257d))

- **kanbus**: Pr #80 revision for Tactus lockfile
  ([`bd01f31`](https://github.com/AnthusAI/Limatus/commit/bd01f31d7d9eef2adadb85901e02466ab0c98ee0))

- **kanbus**: Start LIM-81ecb1 eval CI and fixture corpus close-out
  ([`5788855`](https://github.com/AnthusAI/Limatus/commit/5788855be56a8a6bdf1d259be45a3cda326196fa))

Offline runner already exists (LIM-c1a014). Remaining: CI, docs, more fixtures.

### Continuous Integration

- **eval**: Smoke pytest and offline corpus on PRs
  ([#27](https://github.com/AnthusAI/Limatus/pull/27),
  [`588596f`](https://github.com/AnthusAI/Limatus/commit/588596f32c7fa8cd71f865e1bd6f99c72f1ad932))

Add CI workflow for pytest, offline eval corpus, and Behave smoke. Expand editorial corpus fixtures,
  document eval workflow in README, and fix portable profile test to resolve reference samples.

### Features

- **eval**: Report finding precision/recall and option claim flags
  ([#28](https://github.com/AnthusAI/Limatus/pull/28),
  [`6109937`](https://github.com/AnthusAI/Limatus/commit/6109937a0ee988bb2fa77313ef1941777da7aa6c))


## v0.17.1 (2026-09-11)

### Bug Fixes

- **diagnosis**: Lim-ed02c3 ignore image alts and blockquote redundancy
  ([#26](https://github.com/AnthusAI/Limatus/pull/26),
  [`e80298d`](https://github.com/AnthusAI/Limatus/commit/e80298d05902d068cb137121b844f7844fba8267))

* fix(diagnosis): ignore image markdown and blockquote refrain in redundancy

Mask Markdown/HTML image markup before 4-gram shingling and skip redundancy groups whose members all
  start on blockquote lines (LIM-ed02c3).

* fix(diagnosis): skip redundancy when all n-gram hits are quoted material

Per-occurrence quoted context: blockquote lines, emphasis spans, and Markus pull-quote bodies
  (LIM-ed02c3 revision).

### Chores

- **kanbus**: Close HITL apply gate, park usability epic, start LIM-ed02c3
  ([`661db44`](https://github.com/AnthusAI/Limatus/commit/661db44b7ef92f694ed9cab52560b2688a6f228d))

LIM-2d43b1 stays closed. LIM-30ca2a closed (CLI apply gate). LIM-e872b1 returned to open. LIM-ed02c3
  in progress as the last HITL WIP child. LIM-3ff8d0 left open, not started.

- **kanbus**: Close LIM-2d43b1 portable CLI+SDK epic
  ([`84d6818`](https://github.com/AnthusAI/Limatus/commit/84d681805d9d18a3b8ea3802b380a923a20a03b1))

Children are done on main. Papyrus adapter remains LIM-209793 under LIM-3ff8d0.

- **kanbus**: Close LIM-ed02c3 and HITL packets epic
  ([`30bb8c2`](https://github.com/AnthusAI/Limatus/commit/30bb8c2a07b6ecb991e367902e7ff6da9c5bddb1))

#26 landed on main. LIM-0b9d81 children are all closed.

- **kanbus**: Lim-ed02c3 revision for italic and pull-quote refrain
  ([`1f461d9`](https://github.com/AnthusAI/Limatus/commit/1f461d9b2f0efb22eb72c190019128ae55690ef5))

PR #26 image mask stands; live confession liturgy still flagged.

- **kanbus**: Record LIM-ed02c3 worktree
  ([`72bda03`](https://github.com/AnthusAI/Limatus/commit/72bda03004c5fdcbe014dc6f14f6f16327c3d8b6))

Composer worktree /tmp/limatus-ed02c3-redundancy on fix/LIM-ed02c3-redundancy-alts.


## v0.17.0 (2026-09-11)

### Features

- Explicit pass/fail verdict on the density block
  ([#24](https://github.com/AnthusAI/Limatus/pull/24),
  [`c9b7447`](https://github.com/AnthusAI/Limatus/commit/c9b744756e9ed54a78aa3f2d56f0bd990178b25e))

A diagnosis's `density` block reported raw numbers (wordCount, lexicalDensity, gzipRatio) with no
  verdict. A caller had to already know the profile's thresholds and cross-reference
  `generic_passages` by finding kind to know whether density actually passed.

Adds `skippedTooShort` and `withinThresholds` to `density_summary_as_dict`'s output.
  `withinThresholds` is deliberately `None`, not `True`, when the document is under the profile's
  `minWords` -- `analyze_density` suppresses both real checks in that case, so "too short to judge"
  and "judged and passed" need to stay distinguishable rather than collapsing into one boolean.

`density_summary_as_dict` now takes the profile's `DensityThresholds` and the analysis's findings
  alongside the summary; its one call site (editorial_diagnosis.py) is updated. No other code or
  test in the repo called this function directly, so nothing else needed touching.

Verified: a 2-word draft reports `skippedTooShort: true,

withinThresholds: null`; the real article this whole feedback pass came

from reports `skippedTooShort: false, withinThresholds: true`.

73 pytest tests pass (the same 1 pre-existing, unrelated fixture-path failure as PR #21). Behave: 30
  features / 64 scenarios / 256 steps, all passing, unchanged from #21.

Claude-Session: https://claude.ai/code/session_01VXT47sZM5anEmz8PmN8mbf

Co-authored-by: Claude <noreply@anthropic.com>

- Verify recognizes a reworded claim as preserved, not deleted
  ([#25](https://github.com/AnthusAI/Limatus/pull/25),
  [`0a322c1`](https://github.com/AnthusAI/Limatus/commit/0a322c14fba40313db734e8ba581c58c2703afe7))

verify's diff was exact-string matching: any sentence whose normalized text didn't appear
  byte-for-byte in the working copy was flagged deleted_claim, and any new fact-pattern token
  (including a bare URL) was flagged factual_change_risk -- unconditionally. Every legitimate
  rewrite that touches a fact-bearing sentence looked identical to deleting a claim and inventing a
  new one, whether or not the claim actually survived.

Concretely, this is what motivated the fix: rewording a sentence to add a citation -- exactly what
  this profile's own evidenceRules ask writers to do -- registered as both a deleted_claim (old
  wording gone) and a factual_change_risk (the new URL is a new token). The tool was penalizing the
  edit it was supposed to encourage.

`_claim_preserved` now checks, for a sentence whose exact wording changed: does some working
  sentence contain almost all of the original's own concrete facts (numbers, years, links, absolute
  words), and share enough of its general vocabulary that this isn't a coincidental match between
  two unrelated claims. Both checks are containment (how much of the original survives in the
  candidate), not symmetric Jaccard -- Jaccard penalizes a candidate for containing MORE than the
  original, which is exactly what a citation-adding edit does, and exactly what sentence-merging
  does (two short original sentences folded into one longer working sentence dilutes symmetric
  overlap even when nearly every original word is still present). Verified on a real paragraph that
  both adds nothing but a citation and merges two sentences into one: zero false-positive findings,
  where the previous algorithm flagged it.

`factual_change_risk` (both the score and the finding) now diffs against `_RISK_FACT_PATTERN`, which
  is `_FACT_PATTERN` minus the bare-URL branch: adding a citation to an existing claim must never by
  itself read as introducing a new, unverified fact. A newly added number, year, or absolute word
  still does -- that is a real new claim.

Three new tests lock in the distinction this fix exists to draw: a reworded sentence with an added
  citation is not a deleted claim; adding a citation to an existing number is not a new risk; a
  sentence whose claim is actually different (not just reworded) is still flagged. All four
  pre-existing verifier tests are unchanged and still pass.

76 pytest tests pass (7 in test_verifier.py, up from 4; same 1 pre-existing, unrelated fixture-path
  failure as #21/#22). Behave: 30 features / 64 scenarios / 256 steps, all passing, unchanged.

Claude-Session: https://claude.ai/code/session_01VXT47sZM5anEmz8PmN8mbf

Co-authored-by: Claude <noreply@anthropic.com>


## v0.16.3 (2026-09-11)

### Bug Fixes

- Three quiet correctness gaps found using Limatus on a real draft
  ([#21](https://github.com/AnthusAI/Limatus/pull/21),
  [`2b60c8a`](https://github.com/AnthusAI/Limatus/commit/2b60c8ad164ea9d772db4a0d878d63ccb077cb34))

Found while copy-editing a real Pilobolus article and diagnosed with the help of an Explore agent,
  which pinned exact file/line references for each before any change was made.

1. Silent judge skip. `run_default_judge_lane` returned an empty `JudgeLaneResult` with zero output
  when `OPENAI_API_KEY` was unset and `--require-judge` wasn't passed -- every voice/tone check that
  needs the judge silently did not run, and a diagnosis JSON from that path was indistinguishable
  from "the judge ran and found nothing." The sibling API-error branch already prints a stderr
  notice in this situation; the no-key branch now does too. Closes a real test gap:
  `judge-optional-at-runtime.feature`'s "No key" scenario captured stderr but never asserted on it
  -- it now does.

2. Blockquoted text treated as the narrator's own claim. A Markdown blockquote (quoted human speech,
  e.g. a Reddit comment reproduced in an article) was checked by `_check_unsupported_certainty` and
  `_check_required_facts` as if the *narrator* had asserted it. Added `_is_blockquote_line`, wired
  into both checks -- quoted material is never the narrator's certainty claim.

3. `verify`'s findings were unreadable. `duplication` findings always had `evidence: ""` because
  `_findings` read a `group["excerpt"]` key that repetition groups never set (only each `members[]`
  entry carries one) -- now pulls the actual repeated phrase and notes the repeat count.
  `deleted_claim` and `factual_change_risk` findings had no `rationale` at all, and
  `factual_change_risk`'s evidence was a bare token like "new factual token: 1993" with no context
  -- both now explain themselves, and the latter quotes the sentence that introduced the token when
  one is found.

Also: declares `pytest` in `dev` extras. `tests/` is a pytest suite (bare `assert`, `test_*`
  functions) with no way to run it from a fresh `pip install -e ".[dev]"` today.

Deliberately not touched, and written up separately as design decisions rather than bugs: `verify`'s
  exact-string diff treats every reworded sentence as delete-plus-new-claim (a real algorithm
  change, not a fix); `judge.provider` accepts only "openai" (an existing feature,
  `openai-only-judge-this-stage.feature`, tests specifically that other providers are *rejected* --
  "so we do not pretend multi-provider support exists"); and the `density` block in a diagnosis
  never states a pass/fail verdict, only raw numbers (a schema addition, not a defect).

Verified against the article that surfaced these: 0 findings changed except the three classes above
  (blockquote sentence dropped from `unsupported_claims`; stderr warning now printed; `verify`'s
  duplication findings now show the real repeated phrase).

76 pytest tests pass (1 pre-existing, unrelated failure in test_compare.py -- a fixture resolves
  reference-sample paths against a tempdir that doesn't contain them -- present before this change
  and untouched by it). Behave: 30 features / 64 scenarios / 256 steps, all passing (was 255 steps;
  the new stderr assertion is the added one).

Claude-Session: https://claude.ai/code/session_01VXT47sZM5anEmz8PmN8mbf

Co-authored-by: Claude <noreply@anthropic.com>


## v0.16.2 (2026-09-11)

### Bug Fixes

- **judge**: Body scan blanks YAML so title is a later pass
  ([#20](https://github.com/AnthusAI/Limatus/pull/20),
  [`0e26c24`](https://github.com/AnthusAI/Limatus/commit/0e26c24d8980a3d2b05f3f5e80493fa727812478))

LIM-530ec2: the OpenAI judge was scoring the YAML title. Mask frontmatter the same way the profile
  lane does, drop YAML-span findings/rubric evidence, and bump JUDGE_PROMPT_VERSION with the canary
  pin.

### Chores

- **kanbus**: Close LIM-530ec2 after PR #20
  ([`9db7d0b`](https://github.com/AnthusAI/Limatus/commit/9db7d0babce682d2c9b13b7aa81e7ef1c98749aa))

Judge body scan blanks YAML on main; title and subtitle stay a later pass.


## v0.16.1 (2026-09-11)

### Bug Fixes

- **headline**: Subtitle options must summarize the article under the title
  ([#19](https://github.com/AnthusAI/Limatus/pull/19),
  [`cb68fc3`](https://github.com/AnthusAI/Limatus/commit/cb68fc3f6ca1d29957eadb529b26e6cb930866b6))


## v0.16.0 (2026-09-11)

### Chores

- **kanbus**: Close LIM-565ba8 after PR #18
  ([`bc7346c`](https://github.com/AnthusAI/Limatus/commit/bc7346c3c8edd0b0bbcec2d573cffbba3ed83381))

### Features

- **headline**: Profile-bound title/subtitle HITL after body (LIM-565ba8)
  ([#18](https://github.com/AnthusAI/Limatus/pull/18),
  [`0e2a375`](https://github.com/AnthusAI/Limatus/commit/0e2a3754bdb84e5f9c97848e4e42e8f1a3650e4c))

Add headline schema and CLI options pass, YAML scalar spans for frontmatter fields, and
  suggest_rewrite frontmatter preservation for body-only candidates.


## v0.15.0 (2026-09-11)

### Bug Fixes

- **editorial**: Coalesce unread span prefix onto suffix-start replacements (LIM-af431b)
  ([#17](https://github.com/AnthusAI/Limatus/pull/17),
  [`d2a8006`](https://github.com/AnthusAI/Limatus/commit/d2a80061cc63465c9ce5efda8c640672cedfb7ef))

LLM rewrite options that align with a later substring of the span excerpt are prepended with the
  unread prefix before normalization skip checks and apply, so wiki-janitor options succeed without
  dropping below two options or failing closed at apply time.

### Chores

- **kanbus**: Article then title then subtitle (LIM-565ba8)
  ([`c56dcba`](https://github.com/AnthusAI/Limatus/commit/c56dcbaf4a5d171c4b77e8fd85d40f09b0af27cb))

- **kanbus**: Close LIM-54c503 after PR #16
  ([`baab441`](https://github.com/AnthusAI/Limatus/commit/baab4414f312323430f9d501e6bc1ee6096a7baf))

- **kanbus**: Close LIM-af431b after PR #17
  ([`0183df2`](https://github.com/AnthusAI/Limatus/commit/0183df2cb05eac2462184d6f807b1ef29773ef15))

- **kanbus**: Start headline, compare-CLI, and prefix-coalesce slices
  ([`a14119a`](https://github.com/AnthusAI/Limatus/commit/a14119aa1df400fb9d86acafdd7d1c943d7abbaa))

- **kanbus**: Title and standfirst after body HITL (LIM-565ba8)
  ([`7b1671a`](https://github.com/AnthusAI/Limatus/commit/7b1671ad88167c970ac37ca1050ed81197df026d))

### Features

- **compare**: Wire default guideline alignment resolver (LIM-54c503)
  ([#16](https://github.com/AnthusAI/Limatus/pull/16),
  [`4fa8fa4`](https://github.com/AnthusAI/Limatus/commit/4fa8fa43bc9d10f169abab182ca9fd2e0e1a0145))

Add OpenAI-backed alignment resolution when OPENAI_API_KEY is set, and pass it through limatus
  compare CLI and SDK compare().


## v0.14.4 (2026-09-11)

### Bug Fixes

- **cli**: Publication editorialAim and profile compare constraints (LIM-edbde2)
  ([#15](https://github.com/AnthusAI/Limatus/pull/15),
  [`dad38af`](https://github.com/AnthusAI/Limatus/commit/dad38af75801d185b2a9123e654cc24fbdbf5a21))

### Chores

- **kanbus**: Close LIM-edbde2 after PR #15
  ([`c5abc21`](https://github.com/AnthusAI/Limatus/commit/c5abc21a30f85f2cfc85bbdac5d2431a61bdb7d0))

- **kanbus**: File publication-owned editorialAim for compare
  ([`3d1a902`](https://github.com/AnthusAI/Limatus/commit/3d1a90291d4c5484225bbb0dba48429e663c59e9))

- **kanbus**: Start LIM-edbde2 editorialAim compare layer
  ([`382eb11`](https://github.com/AnthusAI/Limatus/commit/382eb11750b912035ffbf508db62e0acc70e2914))


## v0.14.3 (2026-09-11)

### Bug Fixes

- **cli**: Retry rewrite options after prefix-skip drops (LIM-f634c3)
  ([#14](https://github.com/AnthusAI/Limatus/pull/14),
  [`7745d68`](https://github.com/AnthusAI/Limatus/commit/7745d688fbd9532e3bf7b0d770cb4081722b072c))

When normalization filters prefix-skipping replacements below the two-option minimum, call the
  options resolver once more. The default LLM path adds an extra prompt instruction on retry;
  injected resolvers are invoked again with the same kwargs.

- **cli**: Treat apostrophes as word characters in judge spans (LIM-ce41d9)
  ([#13](https://github.com/AnthusAI/Limatus/pull/13),
  [`ba1e790`](https://github.com/AnthusAI/Limatus/commit/ba1e7902a1862e0e241248d9d9e90631de9ea0f2))

### Chores

- **kanbus**: Close LIM-ce41d9 after PR #13
  ([`36dc655`](https://github.com/AnthusAI/Limatus/commit/36dc655f70cda27d1bbf6064756a0ccc3e861187))

- **kanbus**: Close LIM-f634c3 after PR #14
  ([`4f4317f`](https://github.com/AnthusAI/Limatus/commit/4f4317ffc731fc4d14d2a9b17e4c65fbcb11cb98))

- **kanbus**: Start LIM-ce41d9 apostrophe word-boundary
  ([`2cc746d`](https://github.com/AnthusAI/Limatus/commit/2cc746dba3d9b0a3e157807266f6378b4d751c03))

- **kanbus**: Start LIM-f634c3; file apostrophe span bug
  ([`6810052`](https://github.com/AnthusAI/Limatus/commit/6810052dec1e9e5d2dea512257ede5c7d5fed30b))


## v0.14.2 (2026-09-10)

### Bug Fixes

- **cli**: Reject replacements that skip the span prefix (LIM-073443)
  ([#12](https://github.com/AnthusAI/Limatus/pull/12),
  [`546480c`](https://github.com/AnthusAI/Limatus/commit/546480c37b4a8b30ff4410f32b6006ecd07b0048))

Fail closed on apply when a replacement aligns with a suffix of the span excerpt, and drop such
  options during rewrite normalization.

### Chores

- **kanbus**: Close LIM-073443 after PR #12
  ([`1cb68ad`](https://github.com/AnthusAI/Limatus/commit/1cb68ad03e2e1416a33c96b1bcc85a4ce5da8380))

- **kanbus**: File apply span-prefix drop after wiki-janitor dogfood
  ([`1d1a9df`](https://github.com/AnthusAI/Limatus/commit/1d1a9dfa66a7da361a3bbeee3a36f355ac562b7c))

- **kanbus**: File options retry after prefix-skip filter
  ([`6111fff`](https://github.com/AnthusAI/Limatus/commit/6111fffc4170e384812faa1ef5476175802a4c8e))

- **kanbus**: Start LIM-073443 span-prefix apply fail-closed
  ([`e9b5bad`](https://github.com/AnthusAI/Limatus/commit/e9b5bad0f1061a87309e0303e844b15f6b8aef7c))


## v0.14.1 (2026-09-10)

### Bug Fixes

- **cli**: Drop mid-word judge spans and upsert decisions
  ([#11](https://github.com/AnthusAI/Limatus/pull/11),
  [`9c5ab9d`](https://github.com/AnthusAI/Limatus/commit/9c5ab9dd3ed8faac8ea40993a5dc495de53ac334))

Skip OpenAI judge findings whose spans cut inside a word so apply anchors stay on token boundaries.
  Replace prior decision rows for the same finding_id instead of appending duplicates. Document SDK
  diagnose in README.

### Chores

- **kanbus**: Close LIM-2a1ca5; file LIM-906fc9 dogfood edges
  ([`f444433`](https://github.com/AnthusAI/Limatus/commit/f4444339686bb3a3cc39cd949eace81b1b77f826))

CLI apply on wiki-janitor working copy garbled a mid-word judge span.

- **kanbus**: Close LIM-906fc9 and LIM-c32c24 after PR #11
  ([`593b004`](https://github.com/AnthusAI/Limatus/commit/593b0042640a55a5b1154000bc497f3ef12031b6))

- **kanbus**: Note LIM-2d43b1 remaining Papyrus adapter DoD
  ([`7c2fae7`](https://github.com/AnthusAI/Limatus/commit/7c2fae70627ec0b3ffded062056e2518d9f920f5))


## v0.14.0 (2026-09-10)

### Chores

- **kanbus**: Close LIM-0129cf after PR #10
  ([`8682d94`](https://github.com/AnthusAI/Limatus/commit/8682d94b4e62a2b19a2fcd06749138e2bbc602a7))

CLI scan → decide → apply/diff is on main.

- **kanbus**: Close LIM-79c9b2 and LIM-447936
  ([`478f49e`](https://github.com/AnthusAI/Limatus/commit/478f49e8941f08e2bdefbaf6405b2cb37f98a3f9))

Judge budget landed; scan packets include live Terra judge output.

- **kanbus**: Lim-0129cf Grok plan for CLI loop
  ([`38bcd46`](https://github.com/AnthusAI/Limatus/commit/38bcd46b6fdb9073d6f79b66d553878788650f65))

Composer 2.5 implements decide, __main__, and CLI apply Behave.

- **kanbus**: Lim-0129cf PR #10 opened
  ([`ba4efc1`](https://github.com/AnthusAI/Limatus/commit/ba4efc1e7e4a2d7d864d796dee041d8924daa8d3))

CLI loop review ACCEPT; merge waits on worktree acceptance.

- **kanbus**: Lim-30ca2a blocked on Ryan option choice
  ([`bedde01`](https://github.com/AnthusAI/Limatus/commit/bedde0109b92fff9c67ab8f4f363cb0c4c0ec5d9))

HITL packets ready; no apply until a chosen option id.

- **kanbus**: Park HITL dogfood; start LIM-0129cf CLI
  ([`ba23f97`](https://github.com/AnthusAI/Limatus/commit/ba23f97dab13e8c4e4cf791213b7bd2f3f0d5c38))

Ryan will test after scan → decide → options → compare → apply works as a CLI.

### Features

- **cli**: Python -m limatus entry, decide subcommand, and CLI loop tests
  ([#10](https://github.com/AnthusAI/Limatus/pull/10),
  [`48675ad`](https://github.com/AnthusAI/Limatus/commit/48675ad8f3f2745e7bcb34bf46926816a81dd7d2))

Add __main__ and limatus decide for offline steering decisions; route Behave apply/scan/compare
  steps through python -m limatus and document decide in README.


## v0.13.1 (2026-09-10)

### Bug Fixes

- **judge**: Bounded output token budget for rubric+findings (LIM-79c9b2)
  ([#9](https://github.com/AnthusAI/Limatus/pull/9),
  [`68130ed`](https://github.com/AnthusAI/Limatus/commit/68130ed71505ce73fdbf6de8870a89167f026564))

* fix(judge): raise bounded output token budget for rubric+findings

Hard-coded 2400 max_output_tokens truncated structured judge responses on long Pilobolus drafts with
  required rubric evidence. Use named DEFAULT/MAX judge budgets and draft-scaled helper; generalize
  truncation error wording for non-rewrite callers.

* fix(judge): use 16k floor and 32k cap for finding-heavy scans

Short drafts with dense judge output still truncated at ~8.4k budget because output scales with
  findings and rubric evidence, not draft length. Raise DEFAULT to 16384 for every article and MAX
  to 32768.

### Chores

- **kanbus**: Authorize LIM-79c9b2 judge output budget
  ([`9243b47`](https://github.com/AnthusAI/Limatus/commit/9243b47b30a455948446f0e91fbd3cef6a729597))

Plan approved; implementer to use an isolated worktree off main.

- **kanbus**: File LIM-79c9b2 judge output budget
  ([`7ac10bc`](https://github.com/AnthusAI/Limatus/commit/7ac10bcd6460e0171fb013add369980a5f26ed7c))

Live --require-judge HITL truncated at 2400 output tokens.

- **kanbus**: Lim-79c9b2 16k floor pushed, re-acceptance
  ([`0355aa6`](https://github.com/AnthusAI/Limatus/commit/0355aa6b4c4198bab6b8a74ef5f7c18f8b2dc9f5))

Confession article is the gate after the 8444 truncation reject.

- **kanbus**: Lim-79c9b2 live acceptance reject
  ([`eea3da2`](https://github.com/AnthusAI/Limatus/commit/eea3da22fcb66bc991cc593e8e37de211cb53ad1))

Confession article still truncated; budget must not key off draft length.

- **kanbus**: Lim-79c9b2 PR #9 opened, live acceptance
  ([`d5bf59b`](https://github.com/AnthusAI/Limatus/commit/d5bf59b35b62f31f3744e4b987d0c023d7dcb707))

Unit review passed; merge waits on --require-judge against published copy.


## v0.13.0 (2026-09-10)

### Chores

- **kanbus**: Close LIM-0cd8bf after PR #8 merge
  ([`eb01e90`](https://github.com/AnthusAI/Limatus/commit/eb01e909bb2b3e72d5ca2782367cea4874efba61))

Judge prompt v2 landed on main; HITL re-scan can use house voice.

- **kanbus**: Close LIM-6a6da3 after Papyrus PR #75
  ([`a468483`](https://github.com/AnthusAI/Limatus/commit/a468483786d6902da99d62f7f5463ba4fa415ff8))

Judge enabled on the Pilobolus style profile via develop merge.

### Features

- **judge**: Send full voice config in judge prompt (v2)
  ([#8](https://github.com/AnthusAI/Limatus/pull/8),
  [`3aa6441`](https://github.com/AnthusAI/Limatus/commit/3aa6441cd747bffaece624f08e9af16dbd90af98))

Extend build_judge_user_prompt with sentenceStyle, voicePatterns, structure, and 500-character
  reference excerpts. Bump JUDGE_PROMPT_VERSION and canary pin; add Behave and unit tests without
  live OpenAI.


## v0.12.1 (2026-09-10)

### Bug Fixes

- **judge**: Include rubric in OpenAI structured output required fields
  ([#7](https://github.com/AnthusAI/Limatus/pull/7),
  [`57c5f6e`](https://github.com/AnthusAI/Limatus/commit/57c5f6ecfd8123fb72ad714e56c7b182ccfe6209))

OpenAI Responses rejects schemas when properties keys are missing from required. Align root required
  with findings and rubric; add unit test.

### Chores

- **kanbus**: Agent steers findings; human steers options and feel
  ([`14b37d6`](https://github.com/AnthusAI/Limatus/commit/14b37d64af8e25d966435c9043544f03add2d7eb))

- **kanbus**: Authorize judge schema fix and voice prompt
  ([`7c3956c`](https://github.com/AnthusAI/Limatus/commit/7c3956c79acabf255efe7832d1581a0202e453b5))

- **kanbus**: Authorize Pilobolus judge profile implementation
  ([`4763c2e`](https://github.com/AnthusAI/Limatus/commit/4763c2eac38cd517d8f0f73fa0036ec80e74272a))

- **kanbus**: Close LIM-c31ac3 after PR #7 merge
  ([`45291a1`](https://github.com/AnthusAI/Limatus/commit/45291a18bc68c39cdbd99dd0cceda856c047351c))

- **kanbus**: File HITL dogfood for published Pilobolus
  ([`b991354`](https://github.com/AnthusAI/Limatus/commit/b9913548c190406d65a1f82dbdc17b5fda6d5e3c))

- **kanbus**: Fill LIM-ed02c3 redundancy dogfood story
  ([`2050998`](https://github.com/AnthusAI/Limatus/commit/20509986ed6335cca98882098be84b31096a5c11))

- **kanbus**: Lim-6a6da3 Papyrus PR #75 opened
  ([`cdfb5a1`](https://github.com/AnthusAI/Limatus/commit/cdfb5a119964d37ab289e938a9ec1a6610987088))

- **kanbus**: Live OpenAI judge schema 400 on rubric
  ([`d2b4295`](https://github.com/AnthusAI/Limatus/commit/d2b42954b816dc2a8e930fd57282b9a7e7fa8faa))


## v0.12.0 (2026-09-10)

### Chores

- **kanbus**: Authorize LIM-d895df canary implementation
  ([`2adc561`](https://github.com/AnthusAI/Limatus/commit/2adc5611c7b04a251785f8336e1f5577ec56294e))

- **kanbus**: Close LIM-d895df and LIM-df9d58 after PR #6
  ([`d4a4262`](https://github.com/AnthusAI/Limatus/commit/d4a4262877f6863ad193cc7bda8afc346304b886))

- **kanbus**: Lim-d895df PR #6 opened; acceptance in flight
  ([`c91a4a0`](https://github.com/AnthusAI/Limatus/commit/c91a4a05a7f0f77425e6bdb761cfe02599fbaf9d))

### Features

- **canary**: Add judge calibration fixture runner (LIM-ca93ca)
  ([#6](https://github.com/AnthusAI/Limatus/pull/6),
  [`4a2634b`](https://github.com/AnthusAI/Limatus/commit/4a2634be3ac3bd73b7aac9411ac0cd31e2842810))

Introduce limatus canary with a small checked-in manifest, fixture judge resolver, and calibration
  pins for JUDGE_PROMPT_VERSION and Terra default model. Complements the offline eval harness
  without replacing it.


## v0.11.0 (2026-09-10)

### Chores

- **kanbus**: Authorize LIM-e9176a agent-loop implementation
  ([`29d3bcb`](https://github.com/AnthusAI/Limatus/commit/29d3bcbe80f98214b4f90dfd2bd67cbb53347ba0))

- **kanbus**: Close LIM-e9176a; start LIM-d895df canary plan
  ([`59608f7`](https://github.com/AnthusAI/Limatus/commit/59608f7a052d7284658dbf353815908e6b4e43c9))

- **kanbus**: Lim-e9176a acceptance passed; PR pending
  ([`0ac9904`](https://github.com/AnthusAI/Limatus/commit/0ac99042f7478a611151779ba18f757cb370b009))

### Features

- **editorial**: Agent copy-edit loop wiring (LIM-e9176a)
  ([#5](https://github.com/AnthusAI/Limatus/pull/5),
  [`bd4aa1c`](https://github.com/AnthusAI/Limatus/commit/bd4aa1ceb8033326f4d6da4db14644bb7176376c))

Add read-only patch preview and compare candidate expansion, plus compose_loop_record for audit
  bundles. Ship Behave contracts for explicit finding decisions and agent shortlist before human
  apply.


## v0.10.0 (2026-09-10)

### Chores

- **kanbus**: Close LIM-0e3f4e; start LIM-e9176a loop plan
  ([`c794cfb`](https://github.com/AnthusAI/Limatus/commit/c794cfbc6a1adac240e908fa4e885b7bb85d8934))

- **kanbus**: Lim-0e3f4e PR #4 opened; acceptance in flight
  ([`3622298`](https://github.com/AnthusAI/Limatus/commit/3622298eb5573b92e09741296fe0cf53e0d87f0a))

### Features

- **compare**: Rank candidates with always-lane deltas (LIM-0e3f4e)
  ([#4](https://github.com/AnthusAI/Limatus/pull/4),
  [`c64d3fd`](https://github.com/AnthusAI/Limatus/commit/c64d3fd23cf5fc4949b37d03e730acbabc245bd5))

Add limatus compare for multi-candidate ranking and regression mode with inspectable finding-count
  deltas, hard constraints on unsupported-claim increases, and optional rubric deltas when judge
  rubric is present.

verify and sdk.verify remain compatibility aliases that run compare regression before emitting the
  legacy advisory JSON.


## v0.9.0 (2026-09-10)

### Chores

- **kanbus**: Authorize LIM-0e3f4e compare implementation
  ([`9df08e4`](https://github.com/AnthusAI/Limatus/commit/9df08e489adefdb8ef1635fd488375c7e68adac3))

- **kanbus**: Authorize LIM-9440e9 always-lane implementation
  ([`3af4932`](https://github.com/AnthusAI/Limatus/commit/3af49325b08a125dedf150321e867d5e85b5a9b6))

- **kanbus**: Authorize LIM-f233fb OpenAI judge implementation
  ([`2901574`](https://github.com/AnthusAI/Limatus/commit/2901574e4326a1795250f291645900d286cd553b))

- **kanbus**: Close LIM-9440e9 after PR #2 merge
  ([`2a621b3`](https://github.com/AnthusAI/Limatus/commit/2a621b33af780a8cf83f010ac9d5a3dea5d7a92e))

- **kanbus**: Close LIM-f233fb after PR #3 merge
  ([`bd0b1bd`](https://github.com/AnthusAI/Limatus/commit/bd0b1bd46af4c18e8ebd50438a0a1e47368ce521))

- **kanbus**: Lim-9440e9 acceptance passed; PR blocked on project/ files
  ([`526eab0`](https://github.com/AnthusAI/Limatus/commit/526eab0941feaff16b54f3068db710d7cff3077d))

- **kanbus**: Lim-f233fb acceptance rejected on missing Behave step
  ([`da26e0d`](https://github.com/AnthusAI/Limatus/commit/da26e0d96ae3e10934b7bce7ce4c3e8debabe455))

- **kanbus**: Re-accept LIM-f233fb; start LIM-0e3f4e compare plan
  ([`18fa3cd`](https://github.com/AnthusAI/Limatus/commit/18fa3cd434f0ee27b82c63c3820b52fae0f5bb95))

- **kanbus**: Send LIM-9440e9 plan back for missing worktree
  ([`290859d`](https://github.com/AnthusAI/Limatus/commit/290859df133e9460d330d426cb723ec6e02ea9f8))

### Features

- **judge**: Configured OpenAI judge lane (LIM-f233fb)
  ([#3](https://github.com/AnthusAI/Limatus/pull/3),
  [`4870dc0`](https://github.com/AnthusAI/Limatus/commit/4870dc023cccf184c6981ec19a287ece70e17b3c))

* feat(judge): configured OpenAI judge lane (LIM-f233fb)

Wire live OpenAI judge when OPENAI_API_KEY is set, Terra default model, optional 1-5 rubric
  dimensions, union with profile findings, and --require-judge for hard-fail when the judge cannot
  run. Add verbatim Behave stories and mocked unit coverage; CI stays green without secrets.

* fix(test): register judge findings absent Behave step (LIM-f233fb)

Restore `when` import so editorial_judge_steps loads, and bind "judge findings are absent" to the
  existing no-judge-findings assertion.

### Testing

- **editorial**: Behave always-lane voice-local and density scenarios
  ([#2](https://github.com/AnthusAI/Limatus/pull/2),
  [`8001b5a`](https://github.com/AnthusAI/Limatus/commit/8001b5a0610e525e49d45e16619e97ca6cc497c1))

Add Kanbus LIM-0fa50c and LIM-cebc08 Gherkin with fixtures that prove scan findings differ per
  profile bans and skip document-level density flags for house-voice and sub-minWords drafts.


## v0.8.0 (2026-09-10)

### Chores

- **kanbus**: Approve LIM-3e6cb0 plan; implementation authorized
  ([`6aa5cd3`](https://github.com/AnthusAI/Limatus/commit/6aa5cd34a38f906cc986e0be0fdacff488ce5531))

- **kanbus**: Close LIM-3e6cb0; start always-lane and judge epics
  ([`fe0dbf7`](https://github.com/AnthusAI/Limatus/commit/fe0dbf7fa43e9bec43081a1ed4f3e7f49af69882))

- **kanbus**: Commit board state (issues)
  ([`5ac4b11`](https://github.com/AnthusAI/Limatus/commit/5ac4b1104dc47b3b8bf100b685973be216d0b282))

- **kanbus**: File LIM-df9d58 scan/judge/compare initiative
  ([`e74c3f9`](https://github.com/AnthusAI/Limatus/commit/e74c3f9b96f78432cfdc345a889dfa8303ce59b3))

New initiative with six epics and behavioral stories for the agent-first copy-edit loop. Notes
  successor relationship to LIM-9d14e6.

- **kanbus**: Include event log for board updates
  ([`c600c77`](https://github.com/AnthusAI/Limatus/commit/c600c77b4a57369c28ff7c1a044e9bc34f677812))

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- **kanbus**: Start LIM-3e6cb0 unified scan; planner dispatched
  ([`85581a0`](https://github.com/AnthusAI/Limatus/commit/85581a0aa6f11e558ae1a456e8f2c0abd9af85c1))

### Features

- **scan**: Unified scan surface with finding provenance (LIM-3e6cb0)
  ([#1](https://github.com/AnthusAI/Limatus/pull/1),
  [`53da7ca`](https://github.com/AnthusAI/Limatus/commit/53da7caaa958bb6824cb92d33f1195b36f5cdee5))

* feat(scan): unified scan surface with finding provenance (LIM-3e6cb0)

Add limatus scan as the agent-facing entrypoint with diagnose as an alias, profile/judge source
  fields on findings, stub judge lane with injectable resolver for tests, and Behave coverage for
  the epic acceptance scenarios.

* docs(cli): list scan as primary command in --help text


## v0.7.0 (2026-09-10)

### Features

- Add uncontractedForms check for stated-but-unchecked contraction rules
  ([`f3a62a3`](https://github.com/AnthusAI/Limatus/commit/f3a62a35ce347a5e05d1216d13692a04c4fda0d6))

Caught dogfooding: "That is the same thrift family" shipped in an Anth.us post despite the profile's
  own sentenceStyle explicitly saying "Use contractions and active voice." A prose rule that isn't
  checked gets violated by default, since uncontracted phrasing is exactly what a careful, formal
  draft reaches for without anyone noticing.

checks.uncontractedForms (on by default) flags formal two-word constructions (that is, it is, do
  not, cannot, ...) against their common contraction. Skips the appositive/clarifying "that is,"
  (the "i.e." sense), where contracting would change the meaning.

This needs to vary by publication, not just by individual judgment call: Pilobolus's own VOICE.md
  says the impersonal narrator deliberately avoids contracting ("the narrator stays cool and
  strange"), confirmed against all five of its published articles, so its profile now sets
  uncontractedForms: false. That's a deterministic, profile-level switch -- not left to an agent to
  decide per piece.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>


## v0.6.0 (2026-09-09)

### Features

- Add overusedWords check for crutch-word repetition
  ([`b604708`](https://github.com/AnthusAI/Limatus/commit/b60470869473e9479d399bc8f933b57e59f31a1c))

Caught dogfooding: the Anth.us article this session wrote about Limatus itself used "actually" seven
  times in under a thousand words, and diagnose didn't flag it, because "actually" isn't on anyone's
  bannedIntensifiers list -- it's ordinary English, just not in that quantity. The gap is
  structural: every existing rule-based check requires a publication to name the exact word in
  advance.

checks.overusedWords (on by default) checks a small built-in list of common hedges and crutch words
  (actually, really, very, basically, essentially, literally, simply, clearly, obviously) against
  their own frequency in the document, scaled to length, rather than a fixed per-profile ban list. A
  couple of uses is normal English; seven in a thousand words is a tell no publication should have
  to enumerate by hand.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>


## v0.5.1 (2026-09-09)

### Bug Fixes

- Verify() no longer treats frontmatter edits as factual changes
  ([`ae2dc07`](https://github.com/AnthusAI/Limatus/commit/ae2dc07f3379dbe72e883ce9dee883ed4bd95f30))

diagnose_draft masks a leading YAML frontmatter block before checking prose, but verify_revision
  never did the same for its own text-scanning helpers (_findings, _factual_change_risk,
  _score_draft). Editing a draft's title, date, or description -- normal copyediting -- showed up as
  a "deleted_claim" (the old frontmatter block read as prose that disappeared) and inflated
  factual_change_risk, even when the body was untouched. Found dogfooding verify() on a real
  copy-edit.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>


## v0.5.0 (2026-09-09)

### Features

- Add check_rules for pattern-only checks on non-prose text
  ([`6f7f407`](https://github.com/AnthusAI/Limatus/commit/6f7f407fc0c2a65f140e25d919f7485c1221293b))

diagnose() runs the full heuristic suite -- cadence, redundancy, vague claims, density -- which is
  right for articles but wrong for text that isn't prose at all: a raw .tsx component source, a
  page-content.ts copy string. Those need only the explicit rules (banned phrases/intensifiers/
  patterns, no-emoji, contrast cap), not heuristics tuned for real sentences misfiring on code
  shape.

check_rules_only()/check_rules() run just the rules portion of the pipeline. This is the last piece
  needed to let Chattic.us-web's bespoke check_editorial_rules.py -- the script that inspired
  Limatus in the first place -- call Limatus directly across all three of its surfaces (articles,
  page-content.ts, component sources) instead of maintaining its own duplicate implementation of the
  same rules.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>


## v0.4.0 (2026-09-08)

### Chores

- **kanbus**: Commit board state (issues)
  ([`42fdfb8`](https://github.com/AnthusAI/Limatus/commit/42fdfb8a0fe862889a52f2d4cc056736de278cbe))

- **kanbus**: Record live suggestion dogfood
  ([`dbfbb4e`](https://github.com/AnthusAI/Limatus/commit/dbfbb4e591d7bfec1e9a85ee1f6658b22cfd783c))

### Features

- Add no-emoji ban, per-surface contrast caps, and standfirst checks
  ([`be2d079`](https://github.com/AnthusAI/Limatus/commit/be2d079db6209c555ebe6be6195de2377f40aef4))

Extends the style-profile schema so a single profile can cover what a hand-rolled per-site editorial
  checker was covering separately:

- rules.noEmojis: bans emoji characters outright, checked the same way as banned
  phrases/intensifiers. - rules.bySurface: lets one profile give specific surfaces (marketing,
  legal, etc.) a looser or fully disabled contrast cap instead of forking the whole profile per
  surface. Threaded through diagnose_draft, the CLI's --surface flag, and the SDK's diagnose(). - A
  new standfirst schema block and `limatus standfirst` command/SDK function: checks the parts of a
  good standfirst a script can actually decide -- length, whether it names somebody the reader
  hasn't met yet (capitalized-word heuristic, cross-referenced against an allowlist),
  insider-vocabulary terms and patterns, and how much it overlaps with the article's description.
  Lets a copywriting agent iterate on a candidate sentence before it's written to a file, the way a
  real editorial gate already worked at Chattic.us-web -- ported and generalized from that repo's
  bespoke check_editorial_rules.py rather than reinvented, so a publication doesn't need a one-off
  script to get the same coverage.

Adds features/editorial-surface-rules.feature and features/editorial-standfirst.feature (9 new
  scenarios) alongside a dedicated fixture profile.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>


## v0.3.2 (2026-09-08)

### Bug Fixes

- Handle whole-document suggestion truncation
  ([`6d8b330`](https://github.com/AnthusAI/Limatus/commit/6d8b3301251d58095403531564cef9cd981674c9))

- **kanbus**: Record safety filter false positive
  ([`936fda1`](https://github.com/AnthusAI/Limatus/commit/936fda1bd6dfac230b839989016e284d0611e653))

### Chores

- **kanbus**: Commit board state (issues)
  ([`ff121d4`](https://github.com/AnthusAI/Limatus/commit/ff121d4dcfe63d00b87d1458a4ba1c0a41cef2a8))

- **kanbus**: Commit board state (issues)
  ([`dcc03a5`](https://github.com/AnthusAI/Limatus/commit/dcc03a5111a061ea7b760d50182531d4b7f31382))


## v0.3.1 (2026-09-08)

### Bug Fixes

- **kanbus**: Record holistic suggestion truncation
  ([`1f29906`](https://github.com/AnthusAI/Limatus/commit/1f299061d2c5841779e70af783ae541e5c0bab6b))

### Chores

- **kanbus**: Commit board state (issues)
  ([`dceb53d`](https://github.com/AnthusAI/Limatus/commit/dceb53df6b561e4456d1023b3feb16d78e7252dd))

- **kanbus**: Commit board state (issues)
  ([`8b3475f`](https://github.com/AnthusAI/Limatus/commit/8b3475fa9616d75ec99cd3380ea9f1d27849fb51))

- **kanbus**: Commit board state (issues)
  ([`7a09a83`](https://github.com/AnthusAI/Limatus/commit/7a09a83e20e6f37f3a9c8de438c0b22ef1636369))

- **kanbus**: Commit board state (issues)
  ([`a9088c6`](https://github.com/AnthusAI/Limatus/commit/a9088c63eb4d2f71ad38941a51a0a7b1a07db361))

- **kanbus**: Commit board state (issues)
  ([`138fb15`](https://github.com/AnthusAI/Limatus/commit/138fb155e904c9eb326cc475ffced3585aef2458))

- **kanbus**: Commit board state (issues)
  ([`b2d3624`](https://github.com/AnthusAI/Limatus/commit/b2d3624fae13b9e87691c2cd9092fcd3d6ddfbc3))

- **kanbus**: Commit board state (issues)
  ([`96b7b9b`](https://github.com/AnthusAI/Limatus/commit/96b7b9b50dd03828e0cb2afb8b4a3e83374b393a))

- **kanbus**: Complete composable suggestions
  ([`c1f2837`](https://github.com/AnthusAI/Limatus/commit/c1f28378932f8bf1db2efe3e11cedc2212da6813))

- **kanbus**: Complete revision verifier
  ([`e9044a3`](https://github.com/AnthusAI/Limatus/commit/e9044a36f3c035fc99eabc8fbd52cd36aac78a80))

- **kanbus**: Make editorial suggestions composable
  ([`19bbe6f`](https://github.com/AnthusAI/Limatus/commit/19bbe6f35f0f2943ed88a255338357162a38a5f5))

- **kanbus**: Make holistic suggestions standard
  ([`e70227c`](https://github.com/AnthusAI/Limatus/commit/e70227cae119711347688d8441a5d1b94ce375fb))

- **kanbus**: Record initial live-content dogfood
  ([`42405cb`](https://github.com/AnthusAI/Limatus/commit/42405cbaf25b05581ec4f2b85646ed17fe692889))

- **kanbus**: Reframe holistic suggestions
  ([`d343acc`](https://github.com/AnthusAI/Limatus/commit/d343acc3aa3e0630421da8873b0614c7bc64f9a5))


## v0.3.0 (2026-09-08)

### Chores

- **kanbus**: Commit board state (issues)
  ([`b4c438f`](https://github.com/AnthusAI/Limatus/commit/b4c438f71aedff39e3d8fed9ea27d8752af914cb))

- **kanbus**: Commit board state (issues)
  ([`c85d09d`](https://github.com/AnthusAI/Limatus/commit/c85d09ddf4a8fe001a2d5545c3c629f7264e4c2e))

- **kanbus**: Record completed Luna tasks
  ([`345a101`](https://github.com/AnthusAI/Limatus/commit/345a101fb9a587d2ee14a9ce3f09fd60947a726a))

- **kanbus**: Record task planning events
  ([`a173553`](https://github.com/AnthusAI/Limatus/commit/a173553738e2b141a5deb2d4fa766823bac7ecea))

### Documentation

- Document portable style profiles
  ([`26532a8`](https://github.com/AnthusAI/Limatus/commit/26532a8b4ff7d8eb807c3fb7387372c2f5fadb34))

### Features

- Expose public Limatus Python SDK
  ([`97681bc`](https://github.com/AnthusAI/Limatus/commit/97681bc64464c756447b6a33c731cc9d51d37cb6))


## v0.2.0 (2026-09-08)

### Features

- Add --version/-V flag to the CLI
  ([`0dd1a0c`](https://github.com/AnthusAI/Limatus/commit/0dd1a0cbf64eebf8abb3c362f62202da87879884))

Also serves as the first real conventional-commit release, to verify the python-semantic-release +
  PyPI trusted-publishing pipeline end to end now that the trusted publisher is registered on PyPI.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>


## v0.1.0 (2026-09-08)

### Bug Fixes

- Restore correct starting version after semantic-release misfire
  ([`fbf098e`](https://github.com/AnthusAI/Limatus/commit/fbf098e8fcdeb966e2dd9e89e0f7773820d64480))

python-semantic-release computed its first release purely from conventional-commit history and found
  none, so it defaulted to 0.0.0 and overwrote the version already recorded in pyproject.toml and
  __init__.py, rather than treating that as the starting point. Restores 0.1.0 in both places and
  drops the CHANGELOG.md it generated for the bogus release so a real one gets built cleanly from
  here.

Also drops the defensive "not pytest" framing from the README's Testing section -- naming a tool we
  don't use is a comparison nobody asked for, not information a reader needs.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Chores

- **kanbus**: Commit board state (issues)
  ([`1c4550d`](https://github.com/AnthusAI/Limatus/commit/1c4550da86346fcd58853df6a5c232f7821922b9))

- **kanbus**: Commit board state (issues)
  ([`3931448`](https://github.com/AnthusAI/Limatus/commit/3931448d0b92a41c8ce68a3de93eb668d8f6d47c))
