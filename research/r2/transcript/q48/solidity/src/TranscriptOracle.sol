// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;
import {Transcript512} from "./libraries/Transcript512.sol";
import {Digest512} from "./libraries/Digest512.sol";
import {CanonicalCodec} from "./libraries/CanonicalCodec.sol";
import {Transcript512 as FrozenTranscript} from "../../../../../../contracts/src/libraries/Transcript512.sol";
/// Actual checked API interpreter. No out-of-band mutation labels.
contract TranscriptOracle {
    function replay(Digest512 calldata parameter,uint32[] calldata pv,bytes calldata program)
        external pure returns(bytes memory samples,bytes memory states,uint256 rejectedWords)
    {
        Transcript512.State memory s=Transcript512.initialize(parameter,pv);
        uint256 at;
        while(at<program.length){
            uint8 op; (op,at)=CanonicalCodec.readU8(program,at);
            if(op==0){
                uint16 epoch;uint16 slot;uint8 kind;uint16 len;
                (epoch,at)=CanonicalCodec.readU16(program,at);(slot,at)=CanonicalCodec.readU16(program,at);
                (kind,at)=CanonicalCodec.readU8(program,at);(len,at)=CanonicalCodec.readU16(program,at);
                if(at+len>program.length)revert CanonicalCodec.Truncated();
                Transcript512.observeFrame(s,epoch,slot,kind,program[at:at+len]);at+=len;
            }else{
                uint32 v;
                if(op==1){v=Transcript512.sampleField(s);}else if(op==2){uint8 bits;(bits,at)=CanonicalCodec.readU8(program,at);v=uint32(Transcript512.sampleBits(s,bits));}else revert Transcript512.InvalidFrame();
                samples=bytes.concat(samples,abi.encodePacked(v));states=bytes.concat(states,abi.encodePacked(s.digest.left,s.digest.right));
            }
        }
        if(!Transcript512.finished(s))revert Transcript512.InvalidFrame();
        rejectedWords=s.rejectedWords;
    }
    /// Diagnostic-only old challenger cost on identical observation/sample schedule.
    /// Challenges intentionally differ because the cryptographic configuration differs.
    function frozenReplay(Digest512 calldata parameter,uint32[] calldata pv,bytes calldata program)
        external pure returns(bytes memory samples,bytes memory states)
    {
        FrozenTranscript.State memory s=FrozenTranscript.initialize(parameter,pv);uint256 at;
        while(at<program.length){uint8 op;(op,at)=CanonicalCodec.readU8(program,at);
            if(op==0){uint8 kind;uint16 len;at+=4;(kind,at)=CanonicalCodec.readU8(program,at);(len,at)=CanonicalCodec.readU16(program,at);
                if(kind==1&&len==4){uint32 v;(v,at)=CanonicalCodec.readField(program,at);FrozenTranscript.observeField(s,v);}
                else if(kind==2&&len==64){Digest512 memory v;(v,at)=CanonicalCodec.readDigest(program,at);FrozenTranscript.observeCommitment(s,v);}else revert Transcript512.InvalidFrame();
            }else{uint32 v;if(op==1){v=FrozenTranscript.sampleField(s);}else if(op==2){uint8 bits;(bits,at)=CanonicalCodec.readU8(program,at);v=uint32(FrozenTranscript.sampleBits(s,bits));}else revert Transcript512.InvalidFrame();samples=bytes.concat(samples,abi.encodePacked(v));states=bytes.concat(states,abi.encodePacked(s.digest.left,s.digest.right));}
        }
    }
}
