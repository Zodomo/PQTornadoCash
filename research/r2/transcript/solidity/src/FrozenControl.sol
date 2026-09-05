// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;
import {PQTCVerificationRegistry as FrozenRegistry} from "../../../../../contracts/src/PQTCVerificationRegistry.sol";
import {PQTCAirStageVerifier as FrozenAir} from "../../../../../contracts/src/verifier/PQTCAirStageVerifier.sol";
import {PQTCQueryVerifier as FrozenQuery} from "../../../../../contracts/src/verifier/PQTCQueryVerifier.sol";
import {Digest512 as FrozenDigest} from "../../../../../contracts/src/libraries/Digest512.sol";
contract R2FrozenAir is FrozenAir {}
contract R2FrozenQuery is FrozenQuery {}
contract R2FrozenRegistry is FrozenRegistry {
    constructor(FrozenAir air,FrozenQuery query,FrozenDigest memory parameter) FrozenRegistry(air,query,parameter) {}
}
