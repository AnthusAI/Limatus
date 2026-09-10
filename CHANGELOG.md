# CHANGELOG


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
