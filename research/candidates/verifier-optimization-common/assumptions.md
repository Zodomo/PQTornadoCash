# SP-31 combined assumptions

- Baseline gas and byte values are historic frozen fixture facts, not measurements produced by this package.
- The V9 model allocates the reported MMCS, DEEP-X, and FRI component total uniformly over 32 query positions and solves fixed terms to reproduce 16/16.
- The 64/96 schedules are uniform per-byte floors; each total is the maximum of the standard path and its floor.
- A canonical complete proof is used only when a compatible full-path verifier experiment exists. None is integrated here.
