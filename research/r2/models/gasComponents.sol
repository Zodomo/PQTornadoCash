// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity 0.8.30;

import {BabyBear} from "./libraries/BabyBear.sol";
import {Digest512} from "./libraries/Digest512.sol";
import {KeccakPair512} from "./libraries/KeccakPair512.sol";

/// Research component workloads, NOT a PQTCC10R1 verifier or MMCS acceptance check.
contract GasComponents {
    /// Horner reduction of the actual opened base elements at a declared benchmark alpha.
    /// The scan control measures packed-u32 parsing plus a checksum, not zero-cost parsing.
    function opening(bytes calldata fields, uint256 alpha, bool reduce)
        external view returns (uint256 kernelGas, uint256 checksum)
    {
        require(fields.length % 4 == 0 && fields.length <= 1_000_000);
        BabyBear.check(alpha);
        uint256 start = gasleft();
        for (uint256 i; i < fields.length; i += 4) {
            uint256 value;
            assembly ("memory-safe") { value := shr(224, calldataload(add(fields.offset, i))) }
            BabyBear.check(value);
            checksum = reduce ? BabyBear.add(BabyBear.mul(checksum, alpha), value)
                              : BabyBear.add(checksum, value);
        }
        kernelGas = start - gasleft();
    }

    /// Independent 128-byte node compressions, NOT a connected Merkle reconstruction.
    /// Payloads are pairs of real proof frontier digests; count comes from exact frontier work.
    function nodes(bytes calldata pairs, bool compress)
        external view returns (uint256 kernelGas, bytes32 left, bytes32 right)
    {
        require(pairs.length % 128 == 0 && pairs.length <= 2_000_000);
        uint256 start = gasleft();
        bytes memory payload = new bytes(128);
        for (uint256 i; i < pairs.length; i += 128) {
            assembly ("memory-safe") { calldatacopy(add(payload, 32), add(pairs.offset, i), 128) }
            Digest512 memory digest;
            if (compress) digest = KeccakPair512.hash(0x41, payload);
            else assembly ("memory-safe") {
                mstore(digest, mload(add(payload, 32)))
                mstore(add(digest, 32), mload(add(payload, 96)))
            }
            left ^= digest.left;
            right ^= digest.right;
        }
        kernelGas = start - gasleft();
    }
}
