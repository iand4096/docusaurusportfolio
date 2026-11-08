"""Build a complete local snapshot after existing repo governance passes."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import tempfile
from app.config import get_settings
from app.ingest import documents, manifest_hash, taxonomy, validate_source


def build(repo: Path, data_dir: Path, base_url: str, model_name: str, keyword_only: bool = False,
          skip_governance: bool = False) -> dict:
    if not skip_governance:
        validate_source(repo)
    rows = documents(repo,base_url)
    if not rows:
        raise ValueError('No indexable documentation chunks found')
    tax = taxonomy(repo)
    meta = {'source_hash':manifest_hash(repo), 'taxonomy_version':tax.get('version'),
            'chunks':len(rows), 'embedding_model':None if keyword_only else model_name,
            'semantic_enabled':not keyword_only}
    data_dir.mkdir(parents=True,exist_ok=True)
    # Build everything in a staging directory. Swap files only after successful build.
    with tempfile.TemporaryDirectory(dir=data_dir) as tmp:
        staging = Path(tmp)
        (staging/'chunks.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        if not keyword_only:
            import faiss
            import numpy as np
            from sentence_transformers import SentenceTransformer
            encoder = SentenceTransformer(model_name)
            vectors = np.asarray(encoder.encode([r['title']+'\n'+r['heading']+'\n'+r['text'] for r in rows],
                                    normalize_embeddings=True),dtype='float32')
            index = faiss.IndexFlatIP(vectors.shape[1]); index.add(vectors)
            faiss.write_index(index,str(staging/'vectors.faiss'))
        (staging/'manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
        # Local MVP: replace files after all generation succeeds. Stop API during rebuild.
        for name in ('chunks.json','vectors.faiss','manifest.json'):
            src = staging/name
            if src.exists():
                os.replace(src,data_dir/name)
        if keyword_only:
            (data_dir/'vectors.faiss').unlink(missing_ok=True)
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--keyword-only',action='store_true',help='Skip downloading embeddings/FAISS; BM25 works')
    parser.add_argument('--skip-governance',action='store_true',help='FOR TEST FIXTURES ONLY; not recommended')
    args=parser.parse_args()
    cfg=get_settings()
    result=build(cfg.repo_root,cfg.index_dir,cfg.site_base_url,cfg.embedding_model,
                 args.keyword_only,args.skip_governance)
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
