# CHANGELOG


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
