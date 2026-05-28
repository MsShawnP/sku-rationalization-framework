# Test conventions for this project's `tests/`

This file applies when Claude is working in `sku-rationalization-framework/tests/`.

## What gets tested

- Public-facing scoring functions and behaviors.
- Edge cases surfaced during /clarify.
- Anything in FAILURES.md that has a corresponding fix in code.

## What doesn't need a test

- Glue code (one-line wrappers, trivial mappings).
- Configuration constants.

## Structure

- Mirror the source tree: `src/foo/bar.py` → `tests/foo/test_bar.py`.
- One file per source module unless tests are huge.
- Group related tests by behavior, not by function name.

## Test names

- Pattern: `test_<behavior>_when_<condition>`
- Bad: `test_function_1`, `test_score`
- Good: `test_sku_score_returns_kill_when_fails_two_dimensions`

## Setup and teardown

- Prefer fresh state per test over shared mutable state.
- If setup is heavy (DB, network), pin it explicitly and document why.

## Assertions

- One concept per test.
- Assertions should print useful failure messages.

## Mocks and fakes

- Mock at the boundary (network, filesystem, DB), not internal pure functions.
- If you mock a function, comment why.

## Running

- Tests must be runnable with a single command. Document it in README.md.
- A failing test is more useful than an unrun test.

## When a test fails

- Read the actual output, not what you expected to see.
- Don't suppress with `skip` or `xfail` without a PLAN item to come back.
