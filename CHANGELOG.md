# CHANGELOG


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
