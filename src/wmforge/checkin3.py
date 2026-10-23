"""Serial, resumable Check-in 3 benchmark. See notebooks/03_checkin3_colab.ipynb."""
from __future__ import annotations

import argparse
import contextlib
import gc
import hashlib
import json
import random
import subprocess
import sys
import time
from importlib import metadata
from pathlib import Path

import numpy as np
from PIL import Image

from wmforge import benchmark as b, data
from wmforge.harness import SCHEMES
from wmforge.smoke import TARGET_MODEL, TARGET_REVISION, default_quality


def seed_all(seed):
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def source_identity():
    root=Path(__file__).parent
    return {p.name:b.digest(p) for p in sorted(root.glob('*.py'))}


def environment():
    return dict(sorted((d.metadata['Name'].lower(),d.version) for d in metadata.distributions()))


def check_environment():
    import torch
    import diffusers
    import qrcode, galois, ldpc, markdiffusion  # noqa: F401
    if sys.version_info[:2]!=(3,12):
        raise RuntimeError('Check-in 3 requires Python 3.12')
    if torch.__version__.split('+')[0]!='2.10.0' or torch.version.cuda!='12.8' or not torch.cuda.is_available():
        raise RuntimeError('Check-in 3 requires Torch 2.10.0, CUDA 12.8, and an available GPU')
    if diffusers.__version__!='0.40.0':
        raise RuntimeError('Check-in 3 requires Diffusers 0.40.0')
    direct=json.loads(metadata.distribution('markdiffusion').read_text('direct_url.json') or '{}')
    if direct.get('vcs_info',{}).get('commit_id')!=data.MARKDIFFUSION_SHA:
        raise RuntimeError('MarkDiffusion revision differs from protocol')
    if int(metadata.version('ldpc').split('.')[0])>=2:
        raise RuntimeError('PRC requires ldpc<2')
    return environment()


@contextlib.contextmanager
def single_writer(root):
    """OS advisory lock, released automatically on process death; no stale locks."""
    import fcntl
    root=Path(root)
    root.mkdir(parents=True,exist_ok=True)
    with (root/'writer.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('another worker is writing this output directory') from error
        try:
            yield
        finally:
            fcntl.flock(lock,fcntl.LOCK_UN)


def scheme_calibration(log,scheme,n_watermarked=100,n_unwatermarked=200,n_real=100):
    rows=[r for r in log.rows if r['scheme']==scheme and r['stage']=='baseline']
    groups={k:[r for r in rows if r['kind']==k] for k in ('watermarked','unwatermarked','real')}
    if [len(groups[k]) for k in groups]!=[n_watermarked,n_unwatermarked,n_real]:
        raise ValueError(f'{scheme}: incomplete F1; cannot calibrate or launch attacks')
    if n_unwatermarked!=200:
        raise ValueError('full calibration requires 200 generated negatives')
    tpr=sum(r['native'] for r in groups['watermarked'])/n_watermarked
    fpr=sum(r['native'] for r in groups['unwatermarked'])/n_unwatermarked
    return dict(included=tpr>=.9 and fpr<=.05,native_tpr=tpr,native_generated_fpr=fpr,
                threshold=b.calibrate([r['score'] for r in groups['unwatermarked']]),
                rule='score > threshold',resolution_percentage_points=.5,
                label='empirical calibration operating point',
                calibrated_test='PRC score-only calibrated test' if scheme=='PRC' else 'calibrated score test')


def run_forgery(harness,attacker,ids,prompts,load_cover,log,root,quality_fn=None,max_steps=150):
    from wmforge.imprint import imprint
    root=Path(root)
    quality_fn=quality_fn or default_quality(str(attacker.pipe.device))
    for i,image_id in enumerate(ids):
        key=dict(protocol=b.PROTOCOL,scheme=harness.scheme,stage='imprint',attack='imprint',
                 image_id=str(image_id),kind='forged',step=max_steps)
        final=log.get(**key)
        checkpoint=root/f'checkpoints/{harness.scheme}_{image_id}.pt'
        if final:
            b.verify_artifact(root,final)
            if not checkpoint.exists():
                raise ValueError('measurement exists without its optimizer checkpoint')
            continue
        seed=10000+i
        reference_path=f'images/{harness.scheme}/references/{image_id}.png'
        path=root/reference_path
        if path.exists():
            with Image.open(path) as image:
                reference=image.convert('RGB')
        else:
            seed_all(seed)
            reference=harness.generate(prompts[i],seed,True)
            b.save_image(root,reference_path,reference)
        cover=load_cover(image_id)
        def measure(step,image,seconds):
            relative=f'images/{harness.scheme}/imprint/{image_id}_{step:03d}.png'
            # The image is published only after the checkpoint commits it.
            detection=harness.detect(image)
            quality=quality_fn(cover,image)
            quality={k:(float(v) if np.isfinite(v) else str(v)) for k,v in quality.items()}
            buf=__import__('io').BytesIO()
            image.convert('RGB').save(buf,format='PNG')
            return dict(key,step=step,seed=seed,raw_score=detection.raw_score,score=detection.score,
                        native=detection.is_watermarked,seconds=seconds,artifact=relative,
                        sha256=hashlib.sha256(buf.getvalue()).hexdigest(),**quality)
        def publish(row,image):
            sha=b.save_image(root,row['artifact'],image)
            if sha!=row['sha256']:
                raise ValueError('checkpoint artifact hash mismatch')
            log.append(row)
        seed_all(seed)
        imprint(cover,reference,attacker,max_steps=max_steps,lr=.01,validate_every=10,
                checkpoint_path=checkpoint,measure=measure,publish=publish)


def snapshot_inputs(root,ids,cache):
    root=Path(root)
    hashes={}
    for image_id in ids:
        relative=f'inputs/{image_id}.png'
        path=root/relative
        if not path.exists():
            b.save_image(root,relative,data.load_cover(image_id,cache))
        hashes[relative]=b.digest(path)
    return hashes


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--schemes',nargs='+',choices=list(SCHEMES),default=list(SCHEMES))
    parser.add_argument('--stages',nargs='+',choices=['baseline','imprint','removal'],default=['baseline','imprint','removal'])
    parser.add_argument('--prompts',default='data/prompts_checkin3.txt')
    parser.add_argument('--image-ids',default='data/coco_val2017_checkin3.txt')
    parser.add_argument('--cache',default='data/.cache/coco')
    parser.add_argument('--preflight',type=Path,required=True)
    args=parser.parse_args(argv)
    versions=check_environment()
    pilot=json.loads(args.preflight.read_text())
    if not pilot.get('passed') or pilot['source']!=source_identity() or pilot['environment']!=versions:
        raise ValueError('successful preflight with matching code and environment required')
    prompts=data.read_lines(args.prompts)
    ids=data.read_image_ids(args.image_ids)
    if len(prompts)!=200 or len(ids)!=100 or len(set(prompts))!=200 or len(set(ids))!=100:
        raise ValueError('require committed 200-prompt and 100-photo selections')
    if prompts[:50]!=data.read_lines('data/prompts_checkin1.txt') or ids[:50]!=data.read_image_ids('data/coco_val2017_checkin1.txt'):
        raise ValueError('Check-in 1 input prefixes changed')
    with single_writer(args.out):
        hashes=snapshot_inputs(args.out,ids,args.cache)
        identity=dict(protocol=b.PROTOCOL,model=TARGET_MODEL,revision=TARGET_REVISION,
                      markdiffusion=data.MARKDIFFUSION_SHA,source=source_identity(),environment=versions,
                      prompts=prompts,image_ids=ids,input_sha256=hashes,seed=261,size=512,
                      inference_steps=50,guidance=7.5,precision='float32',imprint_lr=.01,
                      max_steps=150,validate_every=10,counts=dict(watermarked=100,unwatermarked=200,real=100,covers=10),
                      removal=b.ATTACKS,preflight_sha256=b.digest(args.preflight))
        b.bind_manifest(args.out/'manifest.json',identity)
        freeze=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True)
        b.bind_manifest(args.out/'installed-environment.json',dict(versions=versions,pip_freeze=freeze))
        log=b.BenchmarkLog(args.out/'measurements-v2.json')
        for row in log.rows:
            b.verify_artifact(args.out,row)
        def load_cover(image_id):
            with Image.open(args.out/f'inputs/{image_id}.png') as image:
                return image.convert('RGB')
        from wmforge.harness import load_target_pipe,build_harness
        from wmforge.key_state import restore_or_save
        from wmforge.imprint import load_attacker
        import torch
        pipe=load_target_pipe(TARGET_MODEL,TARGET_REVISION,'cuda')
        for scheme in args.schemes:
            seed_all(261+list(SCHEMES).index(scheme))
            harness=build_harness(scheme,pipe,'cuda')
            keypath=args.out/f'keys/{scheme}.pkl'
            if not keypath.exists() and (args.out/f'{scheme}-manifest.json').exists():
                raise ValueError('missing saved key state; refusing to regenerate')
            restore_or_save(harness,pipe,keypath)
            b.bind_manifest(args.out/f'{scheme}-manifest.json',dict(scheme=scheme,key_sha256=b.digest(keypath),run=identity))
            if 'baseline' in args.stages:
                b.run_baselines(harness,prompts,ids,load_cover,log,args.out)
            calibration=scheme_calibration(log,scheme)
            b.bind_manifest(args.out/f'{scheme}-calibration.json',calibration)
            if not calibration['included']:
                print(f'{scheme} excluded: {calibration}',flush=True)
                continue
            if 'imprint' in args.stages:
                attacker=load_attacker(TARGET_MODEL,TARGET_REVISION,'cuda')
                run_forgery(harness,attacker,ids[:10],prompts,load_cover,log,args.out)
                del attacker
                gc.collect(); torch.cuda.empty_cache()
            if 'removal' in args.stages:
                from diffusers import StableDiffusionImg2ImgPipeline
                purifier=StableDiffusionImg2ImgPipeline(**pipe.components)
                b.run_removals(harness,log,args.out,purifier)
                del purifier
            del harness
            print(f'finished {scheme}: {args.stages}',flush=True)


if __name__=='__main__':
    main()
