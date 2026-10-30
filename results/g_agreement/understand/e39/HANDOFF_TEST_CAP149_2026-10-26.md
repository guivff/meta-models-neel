# E39 cap test correction — 2026-10-26

- Updated the budget test to6×13,500=81,000seconds and its corresponding
  over-cap, timing-NO_FIT and late-provider-clock fixtures. All39 CPU tests pass.
- No worker, plan, parity, scientific rule or registered-analysis change.
  No GPU or real registered analysis was run; once-only tests use temporary
  synthetic inputs and guards.
- Integrator: the source/archive and analysis code seals include test_e39.py;
  refresh that test-file binding when packaging this commit, as for the previous
  operational refresh. E39 remains the priority run; leave scientific pins and
  any real once-only guard unchanged.
