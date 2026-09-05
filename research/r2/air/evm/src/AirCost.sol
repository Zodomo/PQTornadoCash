// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

/// Research arithmetic cost prototype, NOT a STARK verifier. The constructor
/// binds a compiler-emitted instruction tape containing the actual AIR constraints.
/// Public periodic evaluations and opening values are supplied by the caller.
contract AirCost {
    uint256 constant P = 2013265921;
    bytes32 public immutable programHash;
    uint256 public immutable inputCount;
    constructor(bytes32 hash, uint256 count) { programHash = hash; inputCount = count; }
    function mul(uint256[4] memory a, uint256[4] memory b) private pure returns (uint256[4] memory r) {
        for (uint256 i; i < 4; ++i) for (uint256 j; j < 4; ++j) {
            uint256 t = mulmod(a[i], b[j], P);
            uint256 k = i + j;
            if (k >= 4) { k -= 4; t = mulmod(t, 11, P); }
            r[k] = addmod(r[k], t, P);
        }
    }
    function evaluate(bytes calldata program, uint256[4][] calldata inputs, uint256[4] calldata alpha)
        external view returns (uint256[4] memory accumulator)
    {
        require(keccak256(program) == programHash && program.length % 12 == 0, "program");
        require(inputs.length == inputCount, "inputs");
        for (uint256 i; i < inputs.length; ++i) for (uint256 j; j < 4; ++j) require(inputs[i][j] < P, "canonical");
        for (uint256 j; j < 4; ++j) require(alpha[j] < P, "alpha");
        uint256[4][] memory nodes = new uint256[4][](program.length / 12);
        for (uint256 i; i < nodes.length; ++i) {
            uint256 at = i * 12;
            uint96 instruction = uint96(bytes12(program[at:at+12]));
            uint256 opcode = instruction >> 64;
            uint256 a = uint32(instruction >> 32);
            uint256 b = uint32(instruction);
            if (opcode == 0) { require(a < P, "constant"); nodes[i][0] = a; }
            else if (opcode == 1) nodes[i] = inputs[a];
            else {
                require(a < i, "dependency");
                if (opcode == 5) {
                    accumulator = mul(accumulator, alpha);
                    for (uint256 j; j < 4; ++j) accumulator[j] = addmod(accumulator[j], nodes[a][j], P);
                } else {
                    require(b < i, "dependency");
                    if (opcode == 4) nodes[i] = mul(nodes[a], nodes[b]);
                    else if (opcode == 2 || opcode == 3) {
                        for (uint256 j; j < 4; ++j) nodes[i][j] = addmod(nodes[a][j], opcode == 2 ? nodes[b][j] : P - nodes[b][j], P);
                    } else revert("opcode");
                }
            }
        }
    }
}
