// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;
import {Digest512} from "./Digest512.sol";
import {KeccakPair512} from "./KeccakPair512.sol";
/// R2 T3-02 q32 H0 challenger. Every observation and sample is runtime checked.
library Transcript512 {
    uint32 internal constant BABY_BEAR_MODULUS = 2_013_265_921;
    struct State {
        Digest512 digest;
        bytes output;
        uint256 outputCursor;
        uint64 squeezeCounter;
        uint16 epoch;
        uint16 slot;
        bytes pending;
        uint256 pendingCursor;
        uint16 remaining;
        bool pow;
        uint256 rejectedWords;
    }
    error InvalidFrame();
    error InvalidField();
    error InvalidSample();
    function initialize(Digest512 memory parameter, uint32[] memory pv) internal pure returns (State memory s) {
        if (pv.length != 64) revert InvalidFrame();
        bytes memory fields = new bytes(256);
        for (uint256 i; i < 64; ++i) {
            if (pv[i] >= BABY_BEAR_MODULUS) revert InvalidField();
            uint32 v = pv[i];
            assembly ("memory-safe") { mstore(add(add(fields,32),mul(i,4)),shl(224,v)) }
        }
        s.digest = KeccakPair512.hash(0x42, abi.encodePacked("PQTCT3-02",parameter.left,parameter.right,uint32(64),fields));
        s.pending = new bytes(808);
    }
    function count(State memory s) private pure returns (uint16) {
        if (s.epoch == 0) return 68;
        if (s.epoch == 1) return 2;
        if (s.epoch == 2) return 2096;
        if (s.epoch <= 11) return 2;
        if (s.epoch == 12) return 14;
        return 0;
    }
    function kind(State memory s) private pure returns (uint8) {
        return (s.epoch == 0 && s.slot == 3) || s.epoch == 1 || (s.epoch >= 3 && s.epoch <= 11 && s.slot == 0) ? 2 : 1;
    }
    function observeFrame(State memory s, uint16 epoch, uint16 slot, uint8 itemKind, bytes memory payload) internal pure {
        if (epoch != s.epoch || slot != s.slot || s.remaining != 0 || slot >= count(s) || itemKind != kind(s)) revert InvalidFrame();
        if (payload.length != (itemKind == 1 ? 4 : 64)) revert InvalidFrame();
        if (itemKind == 1) {
            uint32 v;
            assembly ("memory-safe") { v := shr(224,mload(add(payload,32))) }
            if (v >= BABY_BEAR_MODULUS) revert InvalidField();
        }
        bytes memory pending = s.pending;
        uint256 at = s.pendingCursor;
        uint256 len = payload.length;
        if (at + 7 + len > pending.length) revert InvalidFrame();
        assembly ("memory-safe") {
            let out := add(add(pending,32),at)
            mstore8(out,itemKind)
            mstore(add(out,1),shl(240,slot))
            mstore(add(out,3),shl(224,len))
            mcopy(add(out,7),add(payload,32),len)
        }
        s.pendingCursor = at + 7 + len;
        ++s.slot;
    }
    function observeField(State memory s, uint32 v) internal pure { observeFrame(s,s.epoch,s.slot,1,abi.encodePacked(v)); }
    function observeCommitment(State memory s, Digest512 memory v) internal pure { observeFrame(s,s.epoch,s.slot,2,abi.encodePacked(v.left,v.right)); }
    function flush(State memory s) private pure {
        if (s.remaining != 0) return;
        if (s.epoch > 12 || s.slot != count(s) || s.pendingCursor != s.pending.length) revert InvalidSample();
        s.digest = KeccakPair512.hash(0x46,abi.encodePacked(s.digest.left,s.digest.right,"PQTCT3-02",s.epoch,uint32(s.slot),uint32(s.pending.length),s.pending));
        s.output = ""; s.outputCursor = 0; s.squeezeCounter = 0;
        s.pow = s.epoch >= 3;
        s.remaining = s.epoch == 12 ? 49 : s.pow ? 5 : 4;
    }
    function consume(State memory s) private pure {
        --s.remaining;
        if (s.remaining != 0) return;
        ++s.epoch; s.slot = 0; s.pendingCursor = 0;
        uint256 size = s.epoch == 1 ? 142 : s.epoch == 2 ? 23056 : s.epoch <= 11 ? 82 : s.epoch == 12 ? 154 : 0;
        s.pending = new bytes(size);
    }
    function word(State memory s) private pure returns (uint32 v) {
        if (s.outputCursor == s.output.length) {
            Digest512 memory d = KeccakPair512.hash(0x44,abi.encodePacked(s.digest.left,s.digest.right,s.squeezeCounter));
            ++s.squeezeCounter; s.output = abi.encodePacked(d.left,d.right); s.outputCursor = 0;
        }
        bytes memory output = s.output;
        uint256 at = s.outputCursor;
        assembly ("memory-safe") { v := shr(224,mload(add(add(output,32),at))) }
        s.outputCursor += 4;
    }
    function sampleField(State memory s) internal pure returns (uint32 v) {
        flush(s); if (s.pow || s.epoch == 12) revert InvalidSample();
        while (true) { v = word(s) & 0x7fffffff; if (v < BABY_BEAR_MODULUS) {consume(s); return v;} ++s.rejectedWords; }
        revert InvalidSample();
    }
    function sampleExt4(State memory s) internal pure returns (uint32[4] memory v) { for(uint256 i;i<4;++i) v[i]=sampleField(s); }
    function sampleBits(State memory s, uint256 bits) internal pure returns (uint256 v) {
        flush(s);
        if (bits != (s.pow ? 16 : s.epoch == 12 ? 13 : 0) || bits == 0) revert InvalidSample();
        v = word(s) & ((uint256(1)<<bits)-1); s.pow = false; consume(s);
    }
    function checkWitness(State memory s,uint256 bits,uint32 witness) internal pure returns(bool) {
        if(bits!=16) revert InvalidSample(); observeField(s,witness); return sampleBits(s,bits)==0;
    }
    function finished(State memory s) internal pure returns(bool) {return s.epoch==13 && s.remaining==0;}
}
