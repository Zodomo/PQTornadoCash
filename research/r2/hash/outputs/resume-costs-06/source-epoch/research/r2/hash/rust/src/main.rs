use std::io::{self,BufRead,Write};
use pqtc_r2_hash::{Request,evaluate};
fn main()->Result<(),Box<dyn std::error::Error>>{
    let repeats=std::env::args().nth(1).map(|x|x.parse::<usize>()).transpose()?.unwrap_or(0);
    let stdin=io::stdin();let mut out=io::BufWriter::new(io::stdout().lock());
    for line in stdin.lock().lines(){
        let line=line?;
        let result=(||->Result<serde_json::Value,String>{
            let r:Request=serde_json::from_str(&line).map_err(|e|e.to_string())?;
            let value=evaluate(&r,false)?;let reference=evaluate(&r,true)?;
            if value!=reference{return Err("Rust reference/optimized mismatch".into());}
            let mut timing=Vec::new();
            for is_reference in [true,false]{
                let mut samples=Vec::with_capacity(repeats);
                if repeats>0{std::hint::black_box(evaluate(&r,is_reference)?);}
                for _ in 0..repeats{let start=std::time::Instant::now();std::hint::black_box(evaluate(std::hint::black_box(&r),is_reference)?);samples.push(start.elapsed().as_nanos());}
                let mut sorted=samples.clone();sorted.sort_unstable();
                timing.push(serde_json::json!({"tier":if is_reference{"reference"}else{"optimized"},"samples_ns":samples,"median_ns":sorted.get(repeats/2),"warmup":usize::from(repeats>0)}));
            }
            Ok(serde_json::json!({"output":value,"native_latency":timing,"repetitions":repeats}))
        })();
        let value=match result{Ok(x)=>x,Err(e)=>serde_json::json!({"error":e})};writeln!(out,"{}",value)?;out.flush()?;
    }Ok(())
}
