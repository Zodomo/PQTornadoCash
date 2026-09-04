// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {DigestWidthHarness} from "../src/DigestWidthHarness.sol";

contract DigestWidthGasTest is Test {
    uint8 internal constant PROOF_NODE_TAG = 0x41;

    struct GasRow {
        string id;
        uint256 digestBytes;
        uint256 nodePayloadBytes;
        uint256 hashOnly;
        uint256 storageOnly;
        uint256 hashAndStorage;
    }

    function testExactEncodingAndTruncation() external {
        DigestWidthHarness harness = new DigestWidthHarness();
        bytes memory payload = hex"00112233445566778899aabbccddeeff";
        uint8 tag = 0x7a;
        bytes32 expectedLeft = keccak256(abi.encodePacked(bytes1(uint8(0)), bytes1(tag), payload));
        bytes32 expectedRight = keccak256(abi.encodePacked(bytes1(uint8(1)), bytes1(tag), payload));

        (bytes32 left512, bytes32 right512) = harness.hash512(tag, payload);
        assertEq(left512, expectedLeft);
        assertEq(right512, expectedRight);

        (bytes24 left384, bytes24 right384) = harness.hash384(tag, payload);
        assertEq(left384, bytes24(expectedLeft));
        assertEq(right384, bytes24(expectedRight));

        (bytes20 left320, bytes20 right320) = harness.hash320(tag, payload);
        assertEq(left320, bytes20(expectedLeft));
        assertEq(right320, bytes20(expectedRight));
        assertEq(harness.hash256(tag, payload), expectedLeft);

        harness.store384(left384, right384);
        (bytes32 storedLeft, bytes32 storedRight) = harness.storedWords();
        assertEq(storedLeft, bytes32(left384));
        assertEq(storedRight, bytes32(right384));
        assertEq(uint64(uint256(storedLeft)), 0, "384-bit discarded suffix must be zero");

        DigestWidthHarness harness320 = new DigestWidthHarness();
        harness320.store320(left320, right320);
        (storedLeft, storedRight) = harness320.storedWords();
        assertEq(storedLeft, bytes32(left320));
        assertEq(storedRight, bytes32(right320));
        assertEq(uint96(uint256(storedLeft)), 0, "320-bit discarded suffix must be zero");
    }

    function testCanonicalProfileMicrobenchmark() external {
        GasRow memory row512 = _measure512();
        GasRow memory row384 = _measure384();
        GasRow memory row320 = _measure320();
        GasRow memory row256 = _measure256();

        string memory profile = "sp13-profile";
        vm.serializeString(profile, "solc_version", "0.8.30");
        vm.serializeString(profile, "evm_version", "prague");
        vm.serializeBool(profile, "optimizer", true);
        vm.serializeUint(profile, "optimizer_runs", 200);
        string memory profileJson = vm.serializeBool(profile, "via_ir", true);

        string memory variantsJson = string.concat(
            "[",
            _serializeRow("sp13-512", row512),
            ",",
            _serializeRow("sp13-384", row384),
            ",",
            _serializeRow("sp13-320", row320),
            ",",
            _serializeRow("sp13-256", row256),
            "]"
        );
        string memory json = string.concat(
            "{\"schema\":\"pqtc-sp13-foundry-gas-v1\",",
            "\"measurement_scope\":\"SOLIDITY_MICROBENCHMARK_NOT_FULL_PROTOCOL\",",
            "\"gas_delta_definition\":\"gasleft before minus gasleft after one low-level EVM call; deployment and transaction intrinsic/calldata gas excluded\",",
            "\"storage_transition\":\"cold untouched zero slot to nonzero slot\",",
            "\"compiler_profile\":",
            profileJson,
            ",\"variants\":",
            variantsJson,
            "}"
        );
        vm.writeJson(json, "../outputs/foundry-gas.json");
    }

    function _measure512() private returns (GasRow memory row) {
        bytes memory payload = _payload(128);
        DigestWidthHarness hashHarness = new DigestWidthHarness();
        DigestWidthHarness storeHarness = new DigestWidthHarness();
        DigestWidthHarness combinedHarness = new DigestWidthHarness();
        row = GasRow({
            id: "keccak-pair-512",
            digestBytes: 64,
            nodePayloadBytes: 128,
            hashOnly: _callGas(address(hashHarness), abi.encodeCall(hashHarness.hash512, (PROOF_NODE_TAG, payload))),
            storageOnly: _callGas(address(storeHarness), abi.encodeCall(storeHarness.store512, (bytes32(uint256(1)), bytes32(uint256(2))))),
            hashAndStorage: _callGas(address(combinedHarness), abi.encodeCall(combinedHarness.hashAndStore512, (PROOF_NODE_TAG, payload)))
        });
    }

    function _measure384() private returns (GasRow memory row) {
        bytes memory payload = _payload(96);
        DigestWidthHarness hashHarness = new DigestWidthHarness();
        DigestWidthHarness storeHarness = new DigestWidthHarness();
        DigestWidthHarness combinedHarness = new DigestWidthHarness();
        row = GasRow({
            id: "keccak-pair-trunc-384",
            digestBytes: 48,
            nodePayloadBytes: 96,
            hashOnly: _callGas(address(hashHarness), abi.encodeCall(hashHarness.hash384, (PROOF_NODE_TAG, payload))),
            storageOnly: _callGas(address(storeHarness), abi.encodeCall(storeHarness.store384, (bytes24(uint192(1)), bytes24(uint192(2))))),
            hashAndStorage: _callGas(address(combinedHarness), abi.encodeCall(combinedHarness.hashAndStore384, (PROOF_NODE_TAG, payload)))
        });
    }

    function _measure320() private returns (GasRow memory row) {
        bytes memory payload = _payload(80);
        DigestWidthHarness hashHarness = new DigestWidthHarness();
        DigestWidthHarness storeHarness = new DigestWidthHarness();
        DigestWidthHarness combinedHarness = new DigestWidthHarness();
        row = GasRow({
            id: "keccak-pair-trunc-320",
            digestBytes: 40,
            nodePayloadBytes: 80,
            hashOnly: _callGas(address(hashHarness), abi.encodeCall(hashHarness.hash320, (PROOF_NODE_TAG, payload))),
            storageOnly: _callGas(address(storeHarness), abi.encodeCall(storeHarness.store320, (bytes20(uint160(1)), bytes20(uint160(2))))),
            hashAndStorage: _callGas(address(combinedHarness), abi.encodeCall(combinedHarness.hashAndStore320, (PROOF_NODE_TAG, payload)))
        });
    }

    function _measure256() private returns (GasRow memory row) {
        bytes memory payload = _payload(64);
        DigestWidthHarness hashHarness = new DigestWidthHarness();
        DigestWidthHarness storeHarness = new DigestWidthHarness();
        DigestWidthHarness combinedHarness = new DigestWidthHarness();
        row = GasRow({
            id: "single-keccak-256-lower-bound",
            digestBytes: 32,
            nodePayloadBytes: 64,
            hashOnly: _callGas(address(hashHarness), abi.encodeCall(hashHarness.hash256, (PROOF_NODE_TAG, payload))),
            storageOnly: _callGas(address(storeHarness), abi.encodeCall(storeHarness.store256, (bytes32(uint256(1))))),
            hashAndStorage: _callGas(address(combinedHarness), abi.encodeCall(combinedHarness.hashAndStore256, (PROOF_NODE_TAG, payload)))
        });
    }

    function _callGas(address target, bytes memory data) private returns (uint256 gasUsed) {
        uint256 beforeCall = gasleft();
        (bool success,) = target.call(data);
        gasUsed = beforeCall - gasleft();
        assertTrue(success, "microbenchmark call failed");
    }

    function _payload(uint256 length) private pure returns (bytes memory payload) {
        payload = new bytes(length);
        for (uint256 i; i < length; ++i) payload[i] = bytes1(uint8((i * 29 + 17) & 0xff));
    }

    function _serializeRow(string memory object, GasRow memory row) private returns (string memory) {
        vm.serializeString(object, "id", row.id);
        vm.serializeUint(object, "digest_bytes", row.digestBytes);
        vm.serializeUint(object, "node_payload_bytes", row.nodePayloadBytes);
        vm.serializeUint(object, "hash_only_call_gas", row.hashOnly);
        vm.serializeUint(object, "storage_only_cold_call_gas", row.storageOnly);
        vm.serializeUint(object, "hash_and_storage_cold_call_gas", row.hashAndStorage);
        return vm.serializeString(object, "measurement_scope", "SOLIDITY_MICROBENCHMARK_NOT_FULL_PROTOCOL");
    }
}
