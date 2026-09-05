// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;
import {Roles} from "./Roles.sol";
/// Disposable deposit-only envelope. No withdrawal registry or real custody.
/// Both digest widths occupy exactly two storage words; H5's unused 16 bytes are zero.
contract Deposit {
    Roles public immutable hash;
    uint256 public immutable denomination;
    uint256 private immutable digestWidth;
    uint32 public nextIndex;
    bytes32[2] private scope;
    bytes32[2] private root;
    bytes32[2][21] private zeros;
    bytes32[2][20] private frontier;
    mapping(bytes32=>mapping(bytes32=>bool)) public commitments;
    mapping(bytes32=>mapping(bytes32=>bool)) public knownRoots;
    uint256 private reentrancyState=1;
    event Deposited(bytes32 indexed commitmentLeft,bytes32 indexed commitmentRight,uint32 index,bytes32 rootLeft,bytes32 rootRight,uint256 timestamp);
    modifier nonReentrant(){require(reentrancyState==1,"reentrancy");reentrancyState=2;_;reentrancyState=1;}
    constructor(Roles implementation,bytes32 parameterLeft,bytes32 parameterRight,uint256 amount){
        require(block.chainid<=type(uint64).max,"chain-id");require(amount==0,"synthetic-unfunded-only");hash=implementation;denomination=amount;
        digestWidth=implementation.h0()?16:12;
        bytes memory raw=abi.encodePacked(uint64(block.chainid),address(this),amount,uint8(20),uint32(3),parameterLeft,parameterRight);
        uint256[] memory fields=new uint256[](65);for(uint256 i;i<65;++i){fields[i]=uint256(uint8(raw[2*i]))<<8;if(2*i+1<raw.length)fields[i]|=uint8(raw[2*i+1]);}
        uint256[] memory context=hash.evaluate(1,0,fields);scope=pack(context);uint256[] memory z=hash.evaluate(4,0,context);zeros[0]=pack(z);
        for(uint256 level;level<20;++level){frontier[level]=zeros[level];z=parent(level,z,z);zeros[level+1]=pack(z);}root=pack(z);knownRoots[root[0]][root[1]]=true;
    }
    function pack(uint256[] memory x)private pure returns(bytes32[2] memory out){for(uint256 i;i<x.length;++i)out[i/8]|=bytes32(x[i]<<(224-32*(i%8)));}
    function unpack(bytes32[2] memory x)private view returns(uint256[] memory out){out=new uint256[](digestWidth);for(uint256 i;i<out.length;++i)out[i]=uint32(uint256(x[i/8])>>(224-32*(i%8)));}
    function parent(uint256 level,uint256[] memory a,uint256[] memory b)private view returns(uint256[] memory){uint256[] memory p=new uint256[](a.length+b.length);for(uint256 i;i<a.length;++i)p[i]=a[i];for(uint256 i;i<b.length;++i)p[a.length+i]=b[i];return hash.evaluate(5,level,p);}
    function getScope()external view returns(uint256[] memory){return unpack(scope);}
    function getRoot()external view returns(uint256[] memory){return unpack(root);}
    function deposit(uint256[] calldata commitment)external payable nonReentrant{
        require(msg.value==denomination,"amount");uint256 d=digestWidth;require(commitment.length==d,"count");for(uint256 i;i<d;++i)require(commitment[i]<2013265921,"field");
        bytes32[2] memory key=pack(commitment);require(key[0]!=0||key[1]!=0,"zero-commitment");require(!commitments[key[0]][key[1]],"duplicate");uint32 leafIndex=nextIndex;uint32 index=leafIndex;require(index<1<<20,"full");
        uint256[] memory n=commitment;for(uint256 l;l<20;++l){if(index&1==0){frontier[l]=pack(n);n=parent(l,n,unpack(zeros[l]));}else{n=parent(l,unpack(frontier[l]),n);}index>>=1;}
        bytes32[2] memory current=pack(n);commitments[key[0]][key[1]]=true;knownRoots[current[0]][current[1]]=true;nextIndex=leafIndex+1;root=current;emit Deposited(key[0],key[1],leafIndex,current[0],current[1],block.timestamp);
    }
}
