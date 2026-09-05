#!/usr/bin/env python3
"""Materialize the exact q48 control from the owned q32 verifier, before building.
Only query inventory/capacity boundaries change; AIR/hash/arithmetic are unchanged.
"""
from pathlib import Path
import hashlib, json
HERE=Path(__file__).resolve().parent

def materialize():
    output=HERE/'q48/solidity'
    replacements={
        'libraries/Transcript512.sol': [('s.epoch == 12 ? 33','s.epoch == 12 ? 49')],
        'libraries/PQTCProofCodec.sol': [('QUERY_COUNT = 32','QUERY_COUNT = 48'),('HALF_QUERY_COUNT = 16','HALF_QUERY_COUNT = 24'),('common.firstQueries != 12 && common.firstQueries != 14 && common.firstQueries != 16','common.firstQueries != 22 && common.firstQueries != 24 && common.firstQueries != 26')],
        'verifier/PQTCQueryVerifier.sol': [('count >= 12 && count <= 20','count >= 22 && count <= 26'),('uint32[32] queryIndices','uint32[48] queryIndices'),('uint16(32 - HALF)','uint16(48 - HALF)')],
        'PQTCVerificationRegistry.sol': [('QUERY_COUNT = 32','QUERY_COUNT = 48'),('uint32[32]','uint32[48]'),('split != 12 && split != 14 && split != 16','split != 22 && split != 24 && split != 26'),('!= 32 - split','!= 48 - split')],
    }
    sources={}
    for source in (HERE/'solidity/src').rglob('*.sol'):
        relative=source.relative_to(HERE/'solidity/src');text=source.read_text()
        for old,new in replacements.get(str(relative),[]):
            if old not in text:raise ValueError(f'q48 specialization source changed: {relative}: {old}')
            text=text.replace(old,new)
        text=text.replace('../../../../../contracts/','../../../../../../contracts/')
        target=output/'src'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
        sources[str(relative)]={'q32_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'q48_source_sha256':hashlib.sha256(text.encode()).hexdigest()}
    config=(HERE/'solidity/foundry.toml').read_text().replace('"../../../.."','"../../../../.."')
    (output/'foundry.toml').write_text(config)
    (output.parent/'specialization.json').write_text(json.dumps({'query_count':48,'splits':[[22,26],[24,24],[26,22]],'source_changes':replacements,'hashes':sources,'relation':'unchanged H0','security':'stronger relative query-count control, unqualified','balance':'choose lowest measured max(A,B) over declared splits; no query-linear projection'},indent=2)+'\n')
    return output
if __name__=='__main__':materialize()
