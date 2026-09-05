// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;
import {Poseidon2Kernel} from "frozen-generic/Poseidon2Kernel.sol";
import {P2C16} from "frozen-generic/Poseidon16Candidates.sol";
import {P2C32} from "frozen-generic/Poseidon32Candidates.sol";
import {P2BB512} from "frozen/libraries/P2BB512.sol";
import {PQTCApplicationHash} from "frozen/libraries/PQTCApplicationHash.sol";
import {Digest512} from "frozen/libraries/Digest512.sol";
import {H5Permutation} from "./H5Permutation.sol";

abstract contract Roles {
    uint256 constant BB=2013265921;
    bool public immutable h0;
    constructor(bool isH0){h0=isH0;}
    function _perm(uint256[] memory input) internal view virtual returns(uint256[] memory);
    function _h0(uint256 role,uint256 level,uint256[] memory payload) internal view virtual returns(uint256[] memory out){
        uint256[8] memory tags=[uint256(0),16,17,18,19,32,20,21];
        uint256[] memory s=new uint256[](16);s[4]=1;s[5]=tags[role];s[6]=role==1?129:role==6?72:payload.length*4;s[7]=payload.length;s[8]=level;
        for(uint256 j;j<payload.length;j+=4){for(uint256 i;i<4 && j+i<payload.length;++i)s[i]=addmod(s[i],payload[j+i],BB);s=_perm(s);}
        out=new uint256[](16);for(uint256 b;b<4;++b){if(b!=0)s=_perm(s);for(uint256 i;i<4;++i)out[b*4+i]=s[i];}
    }
    function _compress(uint256[] memory input) internal view returns(uint256[] memory out){
        uint256[] memory copy=new uint256[](input.length);for(uint256 i;i<input.length;++i)copy[i]=input[i];
        uint256[] memory p=_perm(copy);uint256 d=h0?16:12;out=new uint256[](d);for(uint256 i;i<d;++i)out[i]=addmod(p[i],input[i],BB);
    }
    function evaluate(uint256 role,uint256 level,uint256[] memory payload) public view returns(uint256[] memory out){
        require(role>0 && role<=11 && (!h0||role<=9),"role");uint256 d=h0?16:12;
        uint256 count=role==1?65:role==2?d+16:role==3?d+8:role==4?d:role==5?2*d:role==6?36:role==7?4*d:h0?16:32;
        require(payload.length==count,"count");require(role==5?level<20:level==0,"level");
        for(uint256 i;i<count;++i){require(payload[i]<BB,"field");if(role==1||role==6)require(payload[i]<=65535,"u16");}
        if(role==1)require(payload[64]&255==0,"odd-padding");
        if(role==8)return _perm(payload);if(role==9)return _compress(payload);if(h0)return _h0(role,level,payload);
        // Isolated fault-injection kernels; no application entrypoint calls these.
        if(role==10||role==11){uint256[] memory original=new uint256[](32);for(uint256 i;i<32;++i)original[i]=payload[i];uint256[] memory p=_perm(payload);out=new uint256[](role==11?14:12);for(uint256 i;i<out.length;++i)out[i]=addmod(p[i],original[role==10?i+1:i],BB);return out;}
        if(role==1||role==6||role==7){
            out=new uint256[](12);
            for(uint256 b;b<(count+16)/16;++b){uint256[] memory x=new uint256[](32);for(uint256 i;i<12;++i)x[i]=out[i];for(uint256 i;i<16;++i){uint256 j=b*16+i;x[12+i]=j<count?payload[j]:j==count?1:0;}x[28]=role;x[29]=2001;x[30]=role==1?129:role==6?72:48;x[31]=b;out=_compress(x);}return out;
        }
        uint256[] memory x=new uint256[](32);for(uint256 i;i<count;++i)x[i]=payload[i];uint256 at=role==3?20:role==5?24:28;x[at]=role;x[at+1]=2001;x[at+2]=count;x[at+3]=level;return _compress(x);
    }
    function batch(uint256[] calldata roles,uint256[] calldata levels,uint256[][] calldata payloads) external view returns(uint256[][] memory out){require(roles.length==levels.length&&roles.length==payloads.length,"batch-count");out=new uint256[][](roles.length);for(uint256 i;i<roles.length;++i)out[i]=evaluate(roles[i],levels[i],payloads[i]);}
    function hash20(uint256[] memory leaf,uint256[][] memory siblings,uint256 index) external view returns(uint256[] memory){require(siblings.length==20 && index<1<<20,"path");uint256 d=h0?16:12;require(leaf.length==d,"leaf");for(uint256 l;l<20;++l){require(siblings[l].length==d,"sibling");uint256[] memory p=new uint256[](2*d);for(uint256 j;j<d;++j){p[j]=(index&1)==0?leaf[j]:siblings[l][j];p[d+j]=(index&1)==0?siblings[l][j]:leaf[j];}leaf=evaluate(5,l,p);index>>=1;}return leaf;}
}
contract H0Reference is Roles,Poseidon2Kernel {
    constructor()Roles(true)Poseidon2Kernel(16,16,13){}
    function _rc(uint256 section,uint256 i)internal pure override returns(uint256){return P2C16.rc((section<<16)|i);}
    function _diag(uint256 i)internal pure override returns(uint256){return P2C16.diag(i);}
    function _perm(uint256[] memory x)internal view override returns(uint256[] memory){return _permutation(x);}
}
contract H5Reference is Roles,Poseidon2Kernel {
    constructor()Roles(false)Poseidon2Kernel(32,12,30){}
    function _rc(uint256 section,uint256 i)internal pure override returns(uint256){return P2C32.rc((section<<16)|i);}
    function _diag(uint256 i)internal pure override returns(uint256){return P2C32.diag(i);}
    function _perm(uint256[] memory x)internal view override returns(uint256[] memory){return _permutation(x);}
}
contract H5Packed is Roles {
    constructor()Roles(false){}
    function _perm(uint256[] memory x)internal pure override returns(uint256[] memory){uint256[32] memory s;for(uint256 i;i<32;++i)s[i]=x[i];s=H5Permutation.packed(s);for(uint256 i;i<32;++i)x[i]=s[i];return x;}
}
contract H5Straight is Roles {
    constructor()Roles(false){}
    function _perm(uint256[] memory x)internal pure override returns(uint256[] memory){uint256[32] memory s;for(uint256 i;i<32;++i)s[i]=x[i];s=H5Permutation.straight(s);for(uint256 i;i<32;++i)x[i]=s[i];return x;}
}
contract H0Optimized is Roles {
    constructor()Roles(true){}
    function _perm(uint256[] memory x)internal pure override returns(uint256[] memory){uint32[16] memory s;for(uint256 i;i<16;++i)s[i]=uint32(x[i]);s=P2BB512.permute(s);for(uint256 i;i<16;++i)x[i]=s[i];return x;}
    function digest(uint256[] memory x,uint256 at)private pure returns(Digest512 memory){uint32[16] memory a;for(uint256 i;i<16;++i)a[i]=uint32(x[at+i]);return P2BB512.fromFields(a);}
    function secret(uint256[] memory x,uint256 at)private pure returns(bytes32 v){for(uint256 i;i<8;++i)v|=bytes32(x[at+i]<<(224-32*i));}
    function _h0(uint256 role,uint256 level,uint256[] memory x)internal pure override returns(uint256[] memory out){
        Digest512 memory value;
        if(role==1){uint16[65] memory a;for(uint256 i;i<65;++i)a[i]=uint16(x[i]);value=P2BB512.hashU16s65Odd(16,a);}
        else if(role==2)value=PQTCApplicationHash.commitment(digest(x,0),secret(x,16),secret(x,24));
        else if(role==3)value=PQTCApplicationHash.nullifierHash(digest(x,0),secret(x,16));
        else if(role==4)value=PQTCApplicationHash.emptyLeaf(digest(x,0));
        else if(role==5)value=PQTCApplicationHash.merkleNode(uint8(level),digest(x,0),digest(x,16));
        else if(role==6){uint16[36] memory a;for(uint256 i;i<36;++i)a[i]=uint16(x[i]);value=P2BB512.hashU16s36(20,a);}
        else value=PQTCApplicationHash.statementHash(digest(x,0),digest(x,16),digest(x,32),digest(x,48));
        uint32[16] memory f=P2BB512.toFields(value);out=new uint256[](16);for(uint256 i;i<16;++i)out[i]=f[i];
    }
}
