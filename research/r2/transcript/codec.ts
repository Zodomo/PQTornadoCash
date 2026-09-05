import { binding, Transcript, P } from "./transcript.ts";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
const word=(n:number)=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b;};
const domain=(s:string)=>{const b=Buffer.alloc(32);b.write(s);return b;};
class Reader {
    at=0; chunks:Buffer[]=[];
    readonly bytes:Buffer;
    constructor(bytes:Buffer){this.bytes=bytes;}
    take(n:number){if(!Number.isSafeInteger(n)||n<0||this.at+n>this.bytes.length)throw Error("truncated");const b=this.bytes.subarray(this.at,this.at+n);this.at+=n;this.chunks.push(b);return b;}
    u16(){return this.take(2).readUInt16BE();}
    u32(){return this.take(4).readUInt32BE();}
    field(){const v=this.u32();if(v>=P)throw Error("noncanonical");return v;}
    fields(n:number){return Array.from({length:n},()=>this.field());}
    digest(){return this.take(64);}
    finish(){if(this.at!==this.bytes.length)throw Error("trailing");}
}
function eq(a:Uint8Array,b:Uint8Array){if(!Buffer.from(a).equals(Buffer.from(b)))throw Error("binding");}
function global(r:Reader){
    const roots=[r.digest(),r.digest(),r.digest()];
    const local=r.fields(190*4),next=r.fields(190*4),quotient=r.fields(64*4),random=r.fields(4*4),hidden=r.fields(76*4);
    const fri=Array.from({length:9},()=>r.digest()),witness=r.fields(9),final=r.fields(4),queryWitness=r.field();
    return {roots,local,next,quotient,random,hidden,fri,witness,final,queryWitness};
}
function parse(bytes:Buffer,isB:boolean,parameter:Buffer,pv:number[],split:number,queries=32){
    const r=new Reader(bytes);eq(r.take(8),Buffer.from(isB?"PQTCPB04":"PQTCPA04"));if(r.u16()!==4)throw Error("version");eq(r.take(4),Buffer.from([3,9,9,4]));if(r.u16()!==queries||r.u16()!==split||!(queries===48?[22,24,26]:[12,14,16]).includes(split))throw Error("shape");eq(r.digest(),parameter);if(r.u16()!==64)throw Error("public count");if(JSON.stringify(r.fields(64))!==JSON.stringify(pv))throw Error("public values");
    const core=isB?r.digest():null;const globalBinding=r.digest();const globalStart=r.at,g=global(r),globalBytes=bytes.subarray(globalStart,r.at);eq(binding(globalBytes),globalBinding);
    const checkpointBinding=r.digest(),payloadStart=r.at,cpGlobal=r.digest(),state=r.digest();eq(cpGlobal,globalBinding);
    const challenges=r.fields(48);if(r.u16()!==queries)throw Error("query count");const indices=Array.from({length:queries},()=>r.u32());if(indices.some(v=>v>=8192))throw Error("query range");const uniqueCount=r.u16();if(uniqueCount>queries)throw Error("unique count");const unique=Array.from({length:uniqueCount},()=>r.u32());if(JSON.stringify(unique)!==JSON.stringify([...new Set(indices)].sort((a,b)=>a-b)))throw Error("unique order");
    const statementBinding=binding(Buffer.concat([domain("PQTC.R2.V4.STATEMENT"),parameter,...pv.map(word)]));eq(binding(Buffer.concat([domain("PQTC.R2.V4.CHECKPOINT"),statementBinding,binding(bytes.subarray(payloadStart,r.at))])),checkpointBinding);
    const start=r.u16(),count=r.u16();if(start!==(isB?split:0)||count!==(isB?queries-split:split))throw Error("half shape");if(JSON.stringify(Array.from({length:count},()=>r.u32()))!==JSON.stringify(indices.slice(start,start+count)))throw Error("half order");
    for(const [matrices,width] of [[1,8],[1,194],[16,8]]){r.fields(count*matrices*width);r.fields(count*matrices*8);const n=r.u32();if(n>4096)throw Error("frontier bound");r.take(n*64);}
    for(let round=0;round<9;round++){r.fields(count*4);r.fields(count*8);const n=r.u32();if(n>4096)throw Error("frontier bound");r.take(n*64);}
    if(r.u32()!==(isB?0x50424534:0x50414534))throw Error("end");r.finish();
    // Canonical encoder consumes the independently parsed typed field/digest sections.
    const encoded=Buffer.concat(r.chunks);eq(encoded,bytes);
    return {core,globalBinding,checkpointBinding,state,challenges,indices,statementBinding,g,encoded};
}
export function decodeParts(a:Buffer,b:Buffer,parameter:Buffer,pv:number[],split:number,queries=32){
    const pa=parse(a,false,parameter,pv,split,queries),pb=parse(b,true,parameter,pv,split,queries);
    eq(pb.core!,binding(Buffer.concat([domain("PQTC.R2.V4.PROOF"),pa.statementBinding,binding(a)])));eq(pa.globalBinding,pb.globalBinding);eq(pa.checkpointBinding,pb.checkpointBinding);
    const t=new Transcript(parameter,pv,queries);const f=(v:number)=>{const b=Buffer.alloc(4);b.writeUInt32BE(v);t.frame(t.epoch,t.slot,1,b);};const fields=(v:number[])=>v.forEach(f);const cap=(v:Buffer)=>t.frame(t.epoch,t.slot,2,v);const ext=()=>Array.from({length:4},()=>t.field());
    fields([9,8,0]);cap(pa.g.roots[0]);fields(pv);const expected=ext();cap(pa.g.roots[1]);cap(pa.g.roots[2]);expected.push(...ext());
    fields(pa.g.random);fields(pa.g.hidden.slice(0,16));fields(pa.g.local);fields(pa.g.hidden.slice(16,32));fields(pa.g.next);fields(pa.g.hidden.slice(32,48));for(let i=0;i<16;i++){fields(pa.g.quotient.slice(i*16,(i+1)*16));fields(pa.g.hidden.slice(48+i*16,64+i*16));}expected.push(...ext());
    for(let i=0;i<9;i++){cap(pa.g.fri[i]);f(pa.g.witness[i]);if(t.bits(16)!==0)throw Error("commit PoW");expected.push(...ext());}
    fields(pa.g.final);fields(Array(9).fill(1));f(pa.g.queryWitness);if(t.bits(16)!==0)throw Error("query PoW");eq(t.digest,pa.state);const indices=Array.from({length:queries},()=>t.bits(13));if(JSON.stringify(indices)!==JSON.stringify(pa.indices)||JSON.stringify(expected)!==JSON.stringify(pa.challenges))throw Error("transcript checkpoint");
    return {partA:pa.encoded,partB:pb.encoded,queryIndices:indices};
}
if(process.argv[1]?.endsWith("codec.ts")){
    const native=process.argv[2],out=process.argv[3],m=JSON.parse(readFileSync(join(native,"results.json"),"utf8"));const results=[];
    for(const split of m.splits.map((v:any)=>v.first_queries)){const dir=join(native,`split-${split}`),a=readFileSync(join(dir,"part-a.pqtc")),b=readFileSync(join(dir,"part-b.pqtc")),parameter=Buffer.from(m.parameter_id.replace(/^0x/,""),"hex");decodeParts(a,b,parameter,m.public_values,split,m.query_count);const row=JSON.parse(readFileSync(join(dir,"results.json"),"utf8"));let rejected=0;
        for(const mutation of row.mutations){let aa=Buffer.from(a),bb=Buffer.from(b),changed=mutation.part===0?aa:bb;if(mutation.offset!==undefined)changed[mutation.offset]^=1;else if(mutation.mode==="trailing")changed=Buffer.concat([changed,Buffer.from([0])]);else changed=changed.subarray(0,-1);if(mutation.part===0)aa=changed;else bb=changed;try{decodeParts(aa,bb,parameter,m.public_values,split,m.query_count);}catch{rejected++;}}
        if(rejected!==row.mutations.length)throw Error("accepted codec mutation");results.push({split,valid:true,rejected});}
    writeFileSync(out,JSON.stringify({specification:"v4-full512",correctness:results,stage:"typescript-codec-native-artifact-parity",security:"unqualified",privacy:"inherited-unqualified",performance:null,promotion:false},null,2));
}
