// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {
    Digest512,
    IAggregateProofVerifier,
    IRootRegistry,
    NullifierSettlementComponent,
    Payout,
    ProofOnlyBatchSettlement,
    PullPayoutSettlementComponent,
    Withdrawal
} from "../src/ProofOnlyBatchSettlement.sol";

contract ModelRootRegistry is IRootRegistry {
    function isKnownRoot(bytes32 left, bytes32 right) external pure returns (bool) {
        return left != bytes32(0) || right != bytes32(0);
    }
}

contract ModelBindingVerifier is IAggregateProofVerifier {
    bytes32 public expected;

    function setExpected(bytes32 value) external {
        expected = value;
    }

    function verify(bytes32 batchId, bytes calldata) external view returns (bool) {
        return batchId == expected;
    }
}

contract SettlementGasTest is Test {
    uint256 private constant DENOMINATION = 1 ether;
    uint256 private constant FEE = 0.01 ether;
    bytes32 private constant STATEMENT_DOMAIN = keccak256("PQTC.SP70.PUBLIC.STATEMENT.V1");

    struct MeasurementVectors {
        uint256[] grid;
        uint256[] nullifierGas;
        uint256[] unrelatedPayoutGas;
        uint256[] sameUserPayoutGas;
        uint256[] calldataBytes;
        uint256[] calldataZeroBytes;
        uint256[] calldataNonzeroBytes;
        uint256[] activeCalldataFloor;
        uint256[] uniform64Floor;
        uint256[] uniform96Floor;
    }

    struct CalldataStats {
        uint256 length;
        uint256 zero;
        uint256 nonzero;
        uint256 activeFloor;
        uint256 uniform64Floor;
        uint256 uniform96Floor;
    }

    function testMeasureSettlementComponentsOnly() external {
        MeasurementVectors memory measured = _measureGrid();
        _writeMeasurements(measured, _measureSuccessfulPullClaim());
    }

    function _measureGrid() private returns (MeasurementVectors memory measured) {
        measured.grid = _grid();
        uint256 length = measured.grid.length;
        measured.nullifierGas = new uint256[](length);
        measured.unrelatedPayoutGas = new uint256[](length);
        measured.sameUserPayoutGas = new uint256[](length);
        measured.calldataBytes = new uint256[](length);
        measured.calldataZeroBytes = new uint256[](length);
        measured.calldataNonzeroBytes = new uint256[](length);
        measured.activeCalldataFloor = new uint256[](length);
        measured.uniform64Floor = new uint256[](length);
        measured.uniform96Floor = new uint256[](length);

        ProofOnlyBatchSettlement settlement = new ProofOnlyBatchSettlement(
            DENOMINATION, new ModelRootRegistry(), new ModelBindingVerifier()
        );
        for (uint256 g; g < length; ++g) {
            uint256 count = measured.grid[g];
            measured.nullifierGas[g] = _measureNullifier(count);
            measured.unrelatedPayoutGas[g] = _measurePayout(count, false);
            measured.sameUserPayoutGas[g] = _measurePayout(count, true);
            CalldataStats memory calldataStats = _calldataStats(settlement, count);
            measured.calldataBytes[g] = calldataStats.length;
            measured.calldataZeroBytes[g] = calldataStats.zero;
            measured.calldataNonzeroBytes[g] = calldataStats.nonzero;
            measured.activeCalldataFloor[g] = calldataStats.activeFloor;
            measured.uniform64Floor[g] = calldataStats.uniform64Floor;
            measured.uniform96Floor[g] = calldataStats.uniform96Floor;
        }
    }

    function _measureNullifier(uint256 count) private returns (uint256) {
        NullifierSettlementComponent component = new NullifierSettlementComponent();
        return _callGas(address(component), abi.encodeCall(component.consume, (_nullifiers(count))));
    }

    function _measurePayout(uint256 count, bool sameUser) private returns (uint256) {
        PullPayoutSettlementComponent component = new PullPayoutSettlementComponent(DENOMINATION);
        return _callGas(address(component), abi.encodeCall(component.credit, (_payouts(count, sameUser))));
    }

    function _calldataStats(ProofOnlyBatchSettlement settlement, uint256 count)
        private
        view
        returns (CalldataStats memory stats)
    {
        bytes memory publicOnlyCall = abi.encodeCall(settlement.settle, (_withdrawals(settlement, count, false), bytes("")));
        stats.length = publicOnlyCall.length;
        (stats.zero, stats.nonzero) = _byteCounts(publicOnlyCall);
        stats.activeFloor = 21_000 + 10 * stats.zero + 40 * stats.nonzero;
        stats.uniform64Floor = 21_000 + 64 * stats.length;
        stats.uniform96Floor = 21_000 + 96 * stats.length;
    }

    function _writeMeasurements(MeasurementVectors memory measured, uint256 claimGas) private {
        string memory object = "sp70";
        vm.serializeString(object, "schema", "sp70-foundry-components-v1");
        vm.serializeString(object, "measurement_class", "EXACT_FOUNDRY_GASLEFT_DELTA_COMPONENTS_NOT_FULL_SETTLEMENT");
        vm.serializeString(object, "calldata_scope", "EXACT_ABI_CALL_WITH_EMPTY_OUTER_PROOF_NOT_FULL_AGGREGATE_CALLDATA");
        vm.serializeUint(object, "N", measured.grid);
        vm.serializeUint(object, "nullifier_component_gas", measured.nullifierGas);
        vm.serializeUint(object, "unrelated_user_pull_credit_gas", measured.unrelatedPayoutGas);
        vm.serializeUint(object, "same_user_pull_credit_gas", measured.sameUserPayoutGas);
        _writeCalldataMeasurements(object, measured, claimGas);
    }

    function _writeCalldataMeasurements(
        string memory object,
        MeasurementVectors memory measured,
        uint256 claimGas
    ) private {
        vm.serializeUint(object, "public_only_calldata_bytes", measured.calldataBytes);
        vm.serializeUint(object, "public_only_calldata_zero_bytes", measured.calldataZeroBytes);
        vm.serializeUint(object, "public_only_calldata_nonzero_bytes", measured.calldataNonzeroBytes);
        vm.serializeUint(object, "public_only_active_calldata_floor", measured.activeCalldataFloor);
        vm.serializeUint(object, "public_only_uniform64_calldata_floor", measured.uniform64Floor);
        vm.serializeUint(object, "public_only_uniform96_calldata_floor", measured.uniform96Floor);
        string memory json = vm.serializeUint(object, "successful_pull_claim_gas", claimGas);
        vm.writeJson(json, "../outputs/foundry-components.json");
    }

    function testSafetyShellBindsOrderPayoutAndNullifier() external {
        ModelRootRegistry roots = new ModelRootRegistry();
        ModelBindingVerifier verifier = new ModelBindingVerifier();
        ProofOnlyBatchSettlement settlement = new ProofOnlyBatchSettlement(DENOMINATION, roots, verifier);
        Withdrawal[] memory rows = _withdrawals(settlement, 4, false);
        bytes32 identifier = settlement.batchIdentifier(rows);
        verifier.setExpected(identifier);
        vm.deal(address(settlement), 4 * DENOMINATION);

        vm.prank(address(0xA66));
        assertEq(settlement.settle(rows, "model-binding-only"), identifier);
        for (uint256 i; i < rows.length; ++i) {
            assertTrue(settlement.nullifiers(rows[i].nullifier.left, rows[i].nullifier.right));
            assertEq(settlement.credits(rows[i].recipient), DENOMINATION - FEE);
            assertEq(settlement.credits(rows[i].relayer), FEE);
        }
        vm.expectRevert(ProofOnlyBatchSettlement.NullifierSpent.selector);
        settlement.settle(rows, "model-binding-only");
    }

    function testDuplicateNullifierRejectedBeforeAnyCredit() external {
        ModelRootRegistry roots = new ModelRootRegistry();
        ModelBindingVerifier verifier = new ModelBindingVerifier();
        ProofOnlyBatchSettlement settlement = new ProofOnlyBatchSettlement(DENOMINATION, roots, verifier);
        Withdrawal[] memory rows = _withdrawals(settlement, 2, false);
        rows[1].nullifier = rows[0].nullifier;
        _sort(settlement, rows);
        vm.deal(address(settlement), 2 * DENOMINATION);
        vm.expectRevert(ProofOnlyBatchSettlement.DuplicateNullifier.selector);
        settlement.settle(rows, "model-binding-only");
        assertEq(settlement.credits(rows[0].recipient), 0);
        assertFalse(settlement.nullifiers(rows[0].nullifier.left, rows[0].nullifier.right));
    }

    function _callGas(address target, bytes memory data) private returns (uint256 used) {
        uint256 beforeCall = gasleft();
        (bool ok,) = target.call(data);
        used = beforeCall - gasleft();
        assertTrue(ok, "valid component call rejected");
    }

    function _measureSuccessfulPullClaim() private returns (uint256 used) {
        PullPayoutSettlementComponent component = new PullPayoutSettlementComponent(DENOMINATION);
        Payout[] memory rows = _payouts(1, false);
        component.credit(rows);
        vm.deal(address(component), DENOMINATION);
        vm.prank(rows[0].recipient);
        uint256 beforeCall = gasleft();
        (bool ok,) = address(component).call(abi.encodeCall(component.claim, ()));
        used = beforeCall - gasleft();
        assertTrue(ok, "pull claim rejected");
    }

    function _withdrawals(ProofOnlyBatchSettlement settlement, uint256 count, bool sameUser)
        private
        view
        returns (Withdrawal[] memory rows)
    {
        rows = new Withdrawal[](count);
        for (uint256 i; i < count; ++i) {
            rows[i] = Withdrawal({
                root: Digest512(bytes32(uint256(0x100)), bytes32(uint256(0x101))),
                nullifier: Digest512(bytes32(i + 1), bytes32(i + 10_001)),
                recipient: payable(sameUser ? address(0x1000) : address(uint160(0x1000 + i))),
                relayer: payable(sameUser ? address(0x2000) : address(uint160(0x2000 + i))),
                fee: FEE
            });
        }
        _sort(settlement, rows);
    }

    function _sort(ProofOnlyBatchSettlement settlement, Withdrawal[] memory rows) private view {
        for (uint256 i = 1; i < rows.length; ++i) {
            Withdrawal memory value = rows[i];
            bytes32 key = _statementKey(settlement, value);
            uint256 j = i;
            while (j != 0 && _statementKey(settlement, rows[j - 1]) > key) {
                rows[j] = rows[j - 1];
                --j;
            }
            rows[j] = value;
        }
    }

    function _statementKey(ProofOnlyBatchSettlement settlement, Withdrawal memory row) private view returns (bytes32) {
        return keccak256(
            abi.encode(
                STATEMENT_DOMAIN,
                block.chainid,
                address(settlement),
                DENOMINATION,
                row.root.left,
                row.root.right,
                row.nullifier.left,
                row.nullifier.right,
                row.recipient,
                row.relayer,
                row.fee
            )
        );
    }

    function _nullifiers(uint256 count) private pure returns (Digest512[] memory values) {
        values = new Digest512[](count);
        for (uint256 i; i < count; ++i) values[i] = Digest512(bytes32(i + 1), bytes32(i + 10_001));
    }

    function _payouts(uint256 count, bool sameUser) private pure returns (Payout[] memory rows) {
        rows = new Payout[](count);
        for (uint256 i; i < count; ++i) {
            rows[i] = Payout({
                recipient: payable(sameUser ? address(0x1000) : address(uint160(0x1000 + i))),
                relayer: payable(sameUser ? address(0x2000) : address(uint160(0x2000 + i))),
                fee: FEE
            });
        }
    }

    function _byteCounts(bytes memory data) private pure returns (uint256 zero, uint256 nonzero) {
        for (uint256 i; i < data.length; ++i) {
            if (data[i] == 0) ++zero;
            else ++nonzero;
        }
    }

    function _grid() private pure returns (uint256[] memory values) {
        values = new uint256[](7);
        values[0] = 1;
        values[1] = 2;
        values[2] = 4;
        values[3] = 8;
        values[4] = 16;
        values[5] = 32;
        values[6] = 64;
    }
}
