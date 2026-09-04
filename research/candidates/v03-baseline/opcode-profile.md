# C00 opcode profile

**Status: NOT_EVALUATED.** No opcode counts are fabricated from Solidity source or historic aggregate gas.

`verify-all.py` retains one `forge -vvvv` execution trace per exact A/B fixture under `gas/evm/`. For a client transaction, run `opcode-profile.py` with a loopback RPC URL and the A/B transaction hashes. The script requires a `debug_traceTransaction` result with `structLogs`, counts every `op` value, preserves step count/failure/gas fields, and writes `gas/opcode-counts.json` with the client version.

This division keeps three forms of evidence distinct:

1. pool/component gas emitted by the nested Foundry harness;
2. call-level traces from exact retained calldata;
3. opcode counts from a named execution client's transaction trace.

A provider summary, RPC estimate, or report fixture number is not opcode evidence. Public RPC endpoints are refused by the supplied script.
