#!/usr/bin/env python3
"""Parse the v0.3 report inventories; never trusts a copied candidate list."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
REPORT = ROOT / "old_reports/ENGINEERING_REPORT.md"
OUT = ROOT / "research/candidates/v03-baseline/source-hashes.json"
ROW = re.compile(r"^\| `([^`]+)` \| (?:[^|]+\| )?([0-9,]+) \| `([0-9a-f]{64})` \|$")
BASELINE = "00f829001999ee66da6fd5161c4c205c07d0b937"

def parse_section(text: str, start: str, end: str) -> list[dict]:
    section = text.split(start, 1)[1].split(end, 1)[0]
    rows=[]
    for line in section.splitlines():
        match=ROW.match(line)
        if match:
            path, size, digest=match.groups()
            rows.append({"path":path,"bytes":int(size.replace(",","")),"sha256":digest})
    return rows

def verify(rows: list[dict]) -> list[dict]:
    checked=[]
    for expected in rows:
        path=ROOT/expected["path"]
        if not path.is_file(): raise SystemExit(f"missing inventory artifact: {expected['path']}")
        data=path.read_bytes(); actual={"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
        if actual["bytes"] != expected["bytes"] or actual["sha256"] != expected["sha256"]:
            raise SystemExit(f"inventory mismatch: {expected['path']}: expected {expected['bytes']}/{expected['sha256']}, got {actual['bytes']}/{actual['sha256']}")
        checked.append({**expected,"verified":True})
    return checked

def regenerate_parameters() -> dict:
    with tempfile.TemporaryDirectory(prefix="pqtc-v03-params-a-") as a, tempfile.TemporaryDirectory(prefix="pqtc-v03-params-b-") as b:
        command=["cargo","run","--locked","--offline","--quiet","-p","pqtc-cli","--","parameters-generate","--out-dir"]
        subprocess.run(command+[a],cwd=ROOT,check=True)
        subprocess.run(command+[b],cwd=ROOT,check=True)
        files=sorted(p.relative_to(a) for p in Path(a).rglob("*") if p.is_file())
        if files != sorted(p.relative_to(b) for p in Path(b).rglob("*") if p.is_file()): raise SystemExit("parameter regeneration file sets differ")
        expected={Path(row["path"]).relative_to("parameters") for row in generated if row["path"].startswith("parameters/")}
        if set(files) != expected: raise SystemExit(f"parameter regeneration file set differs from report: {sorted(set(files)^expected)}")
        records=[]
        for relative in files:
            first=(Path(a)/relative).read_bytes(); second=(Path(b)/relative).read_bytes(); frozen=(ROOT/"parameters"/relative).read_bytes()
            if first != second: raise SystemExit(f"nondeterministic parameter artifact: {relative}")
            if first != frozen: raise SystemExit(f"regenerated parameter artifact differs from report snapshot: {relative}")
            records.append({"path":f"parameters/{relative}","bytes":len(first),"sha256":hashlib.sha256(first).hexdigest(),"first_equals_second":True,"equals_frozen":True})
        return {"status":"PASS","command":"cargo run --locked --offline --quiet -p pqtc-cli -- parameters-generate --out-dir \"$OUT\"","runs":2,"byte_identical":True,"artifacts":records}

parser=argparse.ArgumentParser()
parser.add_argument("--skip-parameter-regeneration",action="store_true")
args=parser.parse_args()
text=REPORT.read_text()
sources=parse_section(text,"## 18. Complete source inventory","## 19. Solidity declaration completeness manifest")
generated=parse_section(text,"## 20. Generated artifact inventory","## 21. Explicit exclusions")
if len(sources)!=59 or len(generated)!=16: raise SystemExit(f"report inventory parse count mismatch: source={len(sources)}, generated={len(generated)}")
peel=subprocess.run(["git","rev-parse","pqtc-v0.3-research-baseline^{}"],cwd=ROOT,text=True,capture_output=True)
peeled=peel.stdout.strip() if peel.returncode==0 else None
if peeled != BASELINE: raise SystemExit(f"baseline tag peel mismatch: expected {BASELINE}, got {peeled or peel.stderr.strip()}")
record={"candidate_id":"C00/v03-baseline","baseline_tag":"pqtc-v0.3-research-baseline","baseline_commit":BASELINE,"tag_peel_verified":True,"report":"old_reports/ENGINEERING_REPORT.md","source_count":59,"generated_count":16,"sources":verify(sources),"generated":verify(generated)}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
parameter_result={"status":"NOT_EVALUATED","reason":"--skip-parameter-regeneration was supplied"} if args.skip_parameter_regeneration else regenerate_parameters()
(ROOT/"research/candidates/v03-baseline/parameter-reproduction.json").write_text(json.dumps(parameter_result,indent=2,sort_keys=True)+"\n")
print("verified source=59 generated=16 baseline_tag=true parameters="+parameter_result["status"])
