# SP-31 combined assumptions

- The projection anchor is the source-bound v03-fixed-01 run and its hash-checked proof/calldata files; historic report values are only a named comparator.
- The V9 model allocates the explicitly named historic MMCS, DEEP-X, and FRI component total uniformly over 32 query positions, then solves fixed terms to reproduce the current canonical 16/16 execution values.
- The active/64/96 schedules are recomputed from current exact calldata bytes and zero counts; each total is the maximum of the standard path and its floor.
- The canonical proof is consumed for baseline bytes, hashes, and gas. No optimized full verifier is integrated, so no full-path savings are claimed.
