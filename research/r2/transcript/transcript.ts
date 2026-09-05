import { keccak_256 } from "../../../packages/sdk/node_modules/@noble/hashes/sha3.js";
import { readFileSync, writeFileSync } from "node:fs";
export const P = 2013265921;
const cat = (...v: Uint8Array[]) => Buffer.concat(v);
const u16 = (v: number) => { if (!Number.isInteger(v) || v < 0 || v > 65535) throw Error("u16"); const b=Buffer.alloc(2); b.writeUInt16BE(v); return b; };
const u32 = (v: number) => { const b=Buffer.alloc(4); b.writeUInt32BE(v); return b; };
const u64 = (v: bigint) => { const b=Buffer.alloc(8); b.writeBigUInt64BE(v); return b; };
export const binding = (v: Uint8Array) => hash(0x47,v);
const hash = (tag: number, v: Uint8Array) => cat(keccak_256(cat(Buffer.from([0,tag]),v)),keccak_256(cat(Buffer.from([1,tag]),v)));
export class Transcript {
    #digest: Buffer; #epoch=0; #slot=0; #remaining=0; #pow=false; #pending:Buffer[]=[]; #output=Buffer.alloc(0); #at=0; #counter=0n; #rejected:number[]=[];
    #queryCount:number;
    get digest(){return Buffer.from(this.#digest);}
    get epoch(){return this.#epoch;}
    get slot(){return this.#slot;}
    get pow(){return this.#pow;}
    get rejected(){return this.#rejected.slice();}
    constructor(parameter: Uint8Array, pv: number[], queryCount=32) {
        if(queryCount!==32&&queryCount!==48)throw Error("query count");this.#queryCount=queryCount;
        if(parameter.length!==64 || pv.length!==64 || pv.some(v=>!Number.isInteger(v)||v<0||v>=P)) throw Error("init");
        this.#digest=hash(0x42,cat(Buffer.from("PQTCT3-02"),parameter,u32(64),...pv.map(u32)));
    }
    count(){return this.#epoch===0?68:this.#epoch===1?2:this.#epoch===2?2096:this.#epoch<=11?2:this.#epoch===12?14:0;}
    kind(){return (this.#epoch===0&&this.#slot===3)||this.#epoch===1||(this.#epoch>=3&&this.#epoch<=11&&this.#slot===0)?2:1;}
    frame(epoch:number,slot:number,kind:number,payload:Uint8Array){
        if(epoch!==this.#epoch||slot!==this.#slot||this.#remaining!==0||slot>=this.count()||kind!==this.kind()) throw Error("phase/order/type");
        if(payload.length!==(kind===1?4:64)) throw Error("length");
        if(kind===1&&Buffer.from(payload).readUInt32BE()>=P) throw Error("noncanonical");
        this.#pending.push(cat(Buffer.from([kind]),u16(slot),u32(payload.length),payload)); this.#slot++;
    }
    flush(){
        if(this.#remaining) return;
        if(this.#epoch>12||this.#slot!==this.count()) throw Error("early/missing");
        const items=cat(...this.#pending);
        this.#digest=hash(0x46,cat(this.#digest,Buffer.from("PQTCT3-02"),u16(this.#epoch),u32(this.#slot),u32(items.length),items));
        this.#pending=[];this.#output=Buffer.alloc(0);this.#at=0;this.#counter=0n;
        this.#pow=this.#epoch>=3;this.#remaining=this.#epoch===12?this.#queryCount+1:this.#pow?5:4;
    }
    word(){if(this.#at===this.#output.length){this.#output=hash(0x44,cat(this.#digest,u64(this.#counter++)));this.#at=0;}const v=this.#output.readUInt32BE(this.#at);this.#at+=4;return v;}
    consume(){if(--this.#remaining===0){this.#epoch++;this.#slot=0;}}
    field(){this.flush();if(this.#pow||this.#epoch===12)throw Error("wrong sample");for(;;){const v=this.word()&0x7fffffff;if(v<P){this.consume();return v;}this.#rejected.push(v);}}
    bits(n:number){this.flush();if(n!==(this.#pow?16:this.#epoch===12?13:0)||n===0)throw Error("bits");const v=this.word()&(2**n-1);this.#pow=false;this.consume();return v;}
}
export function replay(v:any){
    const t=new Transcript(Buffer.from(v.parameter_id.replace(/^0x/,""),"hex"),v.public_values,v.query_count);let samples=0;const program:Buffer[]=[];
    for(const e of v.events){
        if(e.operation==="frame"){
            const b=Buffer.from(e.canonical,"hex");if(b.subarray(0,8).toString()!=="PQTCT3-02")throw Error("version");
            const epoch=b.readUInt16BE(8), count=b.readUInt32BE(10),len=b.readUInt32BE(14);if(b.length!==18+len)throw Error("frame length");
            let at=18;
            for(let i=0;i<count;i++){const kind=b[at],slot=b.readUInt16BE(at+1),n=b.readUInt32BE(at+3);at+=7;const payload=b.subarray(at,at+n);at+=n;t.frame(epoch,slot,kind,payload);program.push(cat(Buffer.from([0]),u16(epoch),u16(slot),Buffer.from([kind]),u16(n),payload));}
            if(at!==b.length)throw Error("trailing"); t.flush();if(t.digest.toString("hex")!==e.after)throw Error("frame state parity");
        } else {
            const before=t.rejected.length;const bits=t.pow?16:13;const actual=e.operation==="field"?t.field():t.bits(bits);
            program.push(e.operation==="field"?Buffer.from([1]):Buffer.from([2,bits]));
            if(actual!==e.value||JSON.stringify(t.rejected.slice(before))!==JSON.stringify(e.rejected))throw Error("sample parity");samples++;
        }
    }
    if(t.epoch!==13)throw Error("incomplete");return {samples,rejected:t.rejected,program:cat(...program),digest:t.digest.toString("hex")};
}
function misuse(){
    const fresh=()=>new Transcript(Buffer.alloc(64),Array(64).fill(0));let rejected=0;
    const cases=[(t:Transcript)=>t.field(),(t:Transcript)=>t.frame(1,0,1,u32(0)),(t:Transcript)=>t.frame(0,1,1,u32(0)),(t:Transcript)=>t.frame(0,0,2,Buffer.alloc(64)),(t:Transcript)=>t.frame(0,0,1,Buffer.alloc(0)),(t:Transcript)=>t.frame(0,0,1,u32(P)),(t:Transcript)=>{t.frame(0,0,1,u32(0));t.frame(0,0,1,u32(0));},(t:Transcript)=>{t.frame(0,0,1,u32(0));t.field();}];
    for(const c of cases){try{c(fresh());}catch{rejected++;}}if(rejected!==cases.length)throw Error("accepted misuse");return rejected;
}
if(process.argv[1]?.endsWith("transcript.ts")){
    const input=process.argv[2],out=process.argv[3];const result=replay(JSON.parse(readFileSync(input,"utf8")));writeFileSync(out,JSON.stringify({specification:"T3-02",correctness:{samples:result.samples,misuse_rejected:misuse(),rejected_words:result.rejected},privacy:"inherited-p3-hiding-unqualified",security:"experimental-unqualified",stage:"typescript-parity-executed",promotion:false,digest:result.digest},null,2));writeFileSync(out+".program",result.program);
}
