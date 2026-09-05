#!/usr/bin/env -S node --experimental-strip-types
import { poseidon2 } from "../../candidates/hash-compression-common/reference/reference.ts";
import { createInterface } from "node:readline";
import { pathToFileURL } from "node:url";
export type Request = { config:string; role:number; level:number; payload:number[] };
const P=2013265921;
export function compression(x:number[]):number[]{const p=poseidon2(x);return p.slice(0,12).map((v,i)=>(v+x[i])%P);}
export function evaluate(r:Request):number[]{
    if(Object.keys(r).sort().join(",")!=="config,level,payload,role")throw Error("wire fields");
    const h0=r.config==="R2-H0-v03";if(!h0&&r.config!=="R2-H5-complete-v1")throw Error("configuration");
    if(!Number.isInteger(r.role)||!Number.isInteger(r.level))throw Error("role/level integer");
    const d=h0?16:12;const count=[0,65,d+16,d+8,d,2*d,36,4*d,h0?16:32,h0?16:32,h0?0:32,h0?0:32][r.role];
    if(!count||!Array.isArray(r.payload)||r.payload.length!==count||r.level<0||(r.role===5?r.level>=20:r.level!==0))throw Error("count/level");
    if(r.payload.some(x=>!Number.isInteger(x)||x<0||x>=P))throw Error("field");
    if([1,6].includes(r.role)&&(r.payload.some(x=>x>65535)||(r.role===1&&(r.payload[64]&255)!==0)))throw Error("u16/padding");
    const p=r.payload;
    // 10/11 are isolated fault-injection kernels, never application domains.
    if(r.role>=8){const y=poseidon2(p);return r.role===8?y:y.slice(0,r.role===11?14:d).map((v,i)=>(v+p[r.role===10?i+1:i])%P);}
    if(h0){let s=Array(16).fill(0);s.splice(4,5,1,[0,16,17,18,19,32,20,21][r.role],r.role===1?129:r.role===6?72:p.length*4,p.length,r.level);
        for(let j=0;j<p.length;j+=4){for(let i=0;i<4&&j+i<p.length;i++)s[i]=(s[i]+p[j+i])%P;s=poseidon2(s);}
        const out:number[]=[];for(let b=0;b<4;b++){if(b)s=poseidon2(s);out.push(...s.slice(0,4));}return out;
    }
    if([1,6,7].includes(r.role)){let chain=Array(12).fill(0);for(let b=0;b<Math.ceil((p.length+1)/16);b++){const x=Array(32).fill(0);x.splice(0,12,...chain);for(let i=0;i<16;i++){const j=b*16+i;x[12+i]=j<p.length?p[j]:j===p.length?1:0;}x.splice(28,4,r.role,2001,r.role===1?129:r.role===6?72:48,b);chain=compression(x);}return chain;}
    const x=Array(32).fill(0);x.splice(0,p.length,...p);x.splice(r.role===3?20:r.role===5?24:28,4,r.role,2001,p.length,r.level);return compression(x);
}
if(process.argv[1]&&pathToFileURL(process.argv[1]).href===import.meta.url){
    for await(const line of createInterface({input:process.stdin,crlfDelay:Infinity})){
        try{console.log(JSON.stringify({output:evaluate(JSON.parse(line))}));}catch(e){console.log(JSON.stringify({error:String(e)}));}
    }
}
