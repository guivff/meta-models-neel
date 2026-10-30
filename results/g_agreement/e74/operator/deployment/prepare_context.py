"""Create a fresh CPU build context from the exact existing author artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--e74',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();recipe=Path(__file__).resolve().parent
    expected={'vllm_metamodels_glm53_b26f02d.tar.gz':'8d9ca706651a1325c7ad9db78b19989a0f0082944577b310dc5aa0cf95046c82',
              'olens_glm53_usage.py':'ebbd4a1fb0b1cf7673ebbe5e75ee102d6652a789ae3b9f9287c06a9011fcfa42'}
    for name,digest in expected.items():
        if hashlib.sha256((a.e74/'evidence'/name).read_bytes()).hexdigest()!=digest:raise ValueError('author source hash differs')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'vendor').mkdir()
    for name in ['Dockerfile','runtime.lock','build.lock','fork.lock','RECIPE.json','verify_deployment.py']:
        shutil.copyfile(recipe/name,a.out/name)
    for name in expected:shutil.copyfile(a.e74/'evidence'/name,a.out/'vendor'/name)
    print(json.dumps({'status':'CONTEXT_PREPARED_CPU_ONLY','files':8,'model_weights_present':False}))


if __name__=='__main__':main()
