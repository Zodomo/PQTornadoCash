// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

import {H0Sponge} from "../src/H0Sponge.sol";
import {H1Poseidon2} from "../src/Poseidon16Candidates.sol";
import {H3Poseidon2, H4Poseidon2} from "../src/Poseidon24Candidates.sol";
import {H5Poseidon2, H6Poseidon2} from "../src/Poseidon32Candidates.sol";
import {H7RpoM31} from "../src/H7RpoM31.sol";

interface INodeKernel { function node(uint256 level, uint256[] calldata left, uint256[] calldata right) external view returns (uint256[] memory); }

contract ResearchTree {
    INodeKernel public immutable kernel;
    uint256 public immutable digestLength;
    uint256[] public root;

    constructor(INodeKernel kernel_, uint256 digestLength_, bool buildZeroTree) {
        kernel = kernel_; digestLength = digestLength_;
        uint256[] memory zero = new uint256[](digestLength_);
        if (buildZeroTree) {
            for (uint256 level; level < 20; ++level) zero = kernel_.node(level, zero, zero);
        }
        root = zero;
    }

    function computeOnlyInsertion(uint256[] calldata leaf) external view returns (uint256[] memory node_) {
        node_ = leaf;
        uint256[] memory zero = new uint256[](digestLength);
        for (uint256 level; level < 20; ++level) node_ = kernel.node(level, node_, zero);
    }

    function syntheticDepth20RootUpdate(uint256[] calldata leaf) external { uint256[] memory node_ = leaf;
    uint256[] memory zero = new uint256[](digestLength);
    for (uint256 level; level < 20; ++level) node_ = kernel.node(level, node_, zero);
    root = node_; }
}

contract GasBench {
    event Size(string candidate, uint256 runtimeBytes, uint256 initcodeBytes);

    function _lanes(uint256 n) private pure returns (uint256[] memory result) {
        result = new uint256[](n);
        for (uint256 i; i < n; ++i) result[i] = i + 1;
    }

    function testH0Operations() external {
        H0Sponge kernel = new H0Sponge();
        kernel.permutation(_lanes(16));
        kernel.note(_lanes(32)); kernel.nullifier(_lanes(24)); kernel.node(7, _lanes(16), _lanes(16));
        ResearchTree tree = new ResearchTree(INodeKernel(address(kernel)), 16, true);
        tree.computeOnlyInsertion(_lanes(16)); tree.syntheticDepth20RootUpdate(_lanes(16));
        emit Size("H0", address(kernel).code.length, type(H0Sponge).creationCode.length);
    }

    function testH1PrimitiveOnly() external {
        H1Poseidon2 kernel = new H1Poseidon2();
        kernel.permutation(_lanes(16)); kernel.compression(_lanes(16));
        emit Size("H1", address(kernel).code.length, type(H1Poseidon2).creationCode.length);
    }

    function testH3OperationsAndTree() external {
        H3Poseidon2 kernel = new H3Poseidon2();
        kernel.permutation(_lanes(24)); kernel.compression(_lanes(24));
        kernel.note(_lanes(20)); kernel.nullifier(_lanes(20)); kernel.node(7, _lanes(10), _lanes(10));
        ResearchTree tree = new ResearchTree(INodeKernel(address(kernel)), 10, true);
        tree.computeOnlyInsertion(_lanes(10)); tree.syntheticDepth20RootUpdate(_lanes(10));
        emit Size("H3", address(kernel).code.length, type(H3Poseidon2).creationCode.length);
    }

    function testH4PrimitiveOnly() external {
        H4Poseidon2 kernel = new H4Poseidon2();
        kernel.permutation(_lanes(24)); kernel.compression(_lanes(24));
        emit Size("H4", address(kernel).code.length, type(H4Poseidon2).creationCode.length);
    }

    function testH5OperationsAndTree() external {
        H5Poseidon2 kernel = new H5Poseidon2();
        kernel.permutation(_lanes(32)); kernel.compression(_lanes(32));
        kernel.note(_lanes(24)); kernel.nullifier(_lanes(24)); kernel.node(7, _lanes(12), _lanes(12));
        ResearchTree tree = new ResearchTree(INodeKernel(address(kernel)), 12, true);
        tree.computeOnlyInsertion(_lanes(12)); tree.syntheticDepth20RootUpdate(_lanes(12));
        emit Size("H5", address(kernel).code.length, type(H5Poseidon2).creationCode.length);
    }

    function testH6OperationsAndTree() external {
        H6Poseidon2 kernel = new H6Poseidon2();
        kernel.permutation(_lanes(32)); kernel.compression(_lanes(32));
        kernel.note(_lanes(28)); kernel.nullifier(_lanes(28)); kernel.node(7, _lanes(14), _lanes(14));
        ResearchTree tree = new ResearchTree(INodeKernel(address(kernel)), 14, true);
        tree.computeOnlyInsertion(_lanes(14)); tree.syntheticDepth20RootUpdate(_lanes(14));
        emit Size("H6", address(kernel).code.length, type(H6Poseidon2).creationCode.length);
    }

    function testH7PublishedSpongeOperations() external {
        H7RpoM31 kernel = new H7RpoM31();
        kernel.permutation(_lanes(24)); kernel.sponge(_lanes(36));
        kernel.note(_lanes(32)); kernel.nullifier(_lanes(32)); kernel.node(7, _lanes(16), _lanes(16));
        emit Size("H7", address(kernel).code.length, type(H7RpoM31).creationCode.length);
    }

    function testH7ZeroTreeConstructor() external {
        H7RpoM31 kernel = new H7RpoM31();
        new ResearchTree(INodeKernel(address(kernel)), 16, true);
    }

    function testH7ComputeOnlyInsertion() external {
        H7RpoM31 kernel = new H7RpoM31();
        ResearchTree tree = new ResearchTree(INodeKernel(address(kernel)), 16, false);
        tree.computeOnlyInsertion(_lanes(16));
    }

    function testH7SyntheticDepth20RootUpdate() external {
        H7RpoM31 kernel = new H7RpoM31();
        ResearchTree tree = new ResearchTree(INodeKernel(address(kernel)), 16, false);
        tree.syntheticDepth20RootUpdate(_lanes(16));
    }
}
