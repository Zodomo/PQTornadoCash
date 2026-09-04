# C20 assumptions

- The authoritative source is Plonky3 `3152b14a89067c83775a8076cc262ffc48a1fd7c`; the runner rejects a different commit or changed security-critical source file.
- `StdRng::from_os_rng()` obtains unpredictable operating-system entropy on the execution host. The deterministic `SmallRng` fixes public Poseidon2 parameters only and never supplies masks.
- The 4,096-element public polynomial and one public point are a matched C20/C30 opening proxy. They are not a witness, AIR, R1CS, common-corpus derivation, or PQTC public statement.
- Postcard length is the native Rust proof payload length, not a canonical PQTC codec or ABI calldata length.
- `getrusage(RUSAGE_SELF).ru_maxrss` is reported in bytes using the operating system's units; it is a process peak, not isolated prover working-set memory.
- Timings are single-run wall-clock observations and are not timing benchmarks.
- The upstream base-case report is diagnostic only and supplies no accepted end-to-end or QROM security level.
- Frozen v0.3/H0 remains the control: binary depth-20 tree, P2BB512-v1, 16-field digest, and 256 by 190 withdrawal AIR with 1,186 degree-at-most-seven constraints.
