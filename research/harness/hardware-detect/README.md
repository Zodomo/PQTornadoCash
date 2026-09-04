# Hardware and toolchain detection

Capture schema-compatible environment metadata with:

```sh
python3 research/harness/hardware-detect/hardware_detect.py --evm-revision cancun
```

Unavailable executables are retained under `detection.unavailable_tools`; use `--strict-tools` to make missing Rust, Solidity, or Foundry tools fatal.
