// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;
import {PQTCVerificationRegistry} from "./PQTCVerificationRegistry.sol";
import {PQTCAirStageVerifier} from "./verifier/PQTCAirStageVerifier.sol";
import {PQTCQueryVerifier} from "./verifier/PQTCQueryVerifier.sol";
import {Digest512} from "./libraries/Digest512.sol";
// Unique artifact names disambiguate the frozen control imported in the same build.
contract R2TranscriptAir is PQTCAirStageVerifier {}
contract R2TranscriptQuery is PQTCQueryVerifier { constructor(uint16 count) PQTCQueryVerifier(count) {} }
contract R2TranscriptRegistry is PQTCVerificationRegistry {
    constructor(PQTCAirStageVerifier air,PQTCQueryVerifier first,PQTCQueryVerifier second,Digest512 memory parameter)
        PQTCVerificationRegistry(air,first,second,parameter) {}
}
