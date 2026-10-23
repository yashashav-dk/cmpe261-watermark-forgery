"""Check-in 3 protocol, immutable identity, and artifact-backed measurements."""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import random
from pathlib import Path

from PIL import Image, ImageFilter

PROTOCOL = 'checkin3-v2'
ATTACKS = {'jpeg': {'quality':95}, 'blur': {'radius':2},
           'crop': {'ratio':0.8, 'centered':True},
           'purification': {'strength':0.3, 'prompt':''}}
KEYS = ('protocol','scheme','stage','attack','image_id','kind','step')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_bytes(path, payload):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    partial=path.with_suffix(path.suffix+'.part')
    with partial.open('wb') as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial,path)


def bind_manifest(path, identity):
    """Create once; any changed configuration or input rejects resume."""
    path=Path(path)
    payload=canonical(identity).encode()
    if path.exists():
        if path.read_bytes()!=payload:
            raise ValueError(f'run identity differs: {path}; use a fresh output directory')
    else:
        atomic_bytes(path,payload)
    return hashlib.sha256(payload).hexdigest()


class BenchmarkLog:
    """Single-writer, versioned atomic log; historical CSVs remain untouched."""
    def __init__(self,path):
        self.path=Path(path)
        self.rows=[]
        if self.path.exists():
            stored=json.loads(self.path.read_text())
            if stored['schema_version']!=2:
                raise ValueError('unsupported measurement schema')
            self.rows=stored['rows']
        self._index={self.key(r):r for r in self.rows}
        if len(self._index)!=len(self.rows):
            raise ValueError('duplicate measurement keys')

    @staticmethod
    def key(row):
        return tuple(row[k] for k in KEYS)

    def get(self,**key):
        return self._index.get(self.key(key))

    def append(self,row):
        canonical(row)
        key=self.key(row)
        if key in self._index:
            if self._index[key]!=row:
                raise ValueError('measurement already exists with different data')
            return False
        updated=self.rows+[row]
        atomic_bytes(self.path,canonical({'schema_version':2,'rows':updated}).encode())
        self.rows=updated
        self._index[key]=row
        return True


def extend_selection(prefix, pool, n, seed=261):
    if len(set(prefix))!=len(prefix) or n<len(prefix):
        raise ValueError('invalid selection prefix or count')
    remaining=sorted(set(pool)-set(prefix))
    if len(prefix)+len(remaining)<n:
        raise ValueError('insufficient selection pool')
    return list(prefix)+random.Random(seed).sample(remaining,n-len(prefix))


def calibrate(scores):
    """Strict > threshold, at most 2/200 positives; ties lower acceptance."""
    values=sorted(float(s) for s in scores)
    if len(values)!=200 or not all(math.isfinite(s) for s in values):
        raise ValueError('calibration requires 200 finite unwatermarked scores')
    return values[-3]


def budget_rows(rows,step):
    return [r for r in rows if r['stage']=='imprint' and r['step']==step]


def save_image(root,relative,image):
    buf=io.BytesIO()
    image.convert('RGB').save(buf,format='PNG')
    atomic_bytes(Path(root)/relative,buf.getvalue())
    return digest(Path(root)/relative)


def verify_artifact(root,row):
    path=Path(root)/row['artifact']
    if not path.is_file() or digest(path)!=row['sha256']:
        raise ValueError(f'missing or modified measured artifact: {path}')


def measurement(harness,image,key,root,relative,**extra):
    sha=save_image(root,relative,image)
    # Evaluate precisely the persisted pixels, including JPEG round trips.
    with Image.open(Path(root)/relative) as saved:
        detection=harness.detect(saved.convert('RGB'))
    return dict(key,raw_score=detection.raw_score,score=detection.score,
                native=detection.is_watermarked,artifact=relative,sha256=sha,**extra)


def run_baselines(harness,prompts,ids,load_cover,log,root,
                  n_watermarked=100,n_unwatermarked=200,n_real=100):
    if len(prompts)<max(n_watermarked,n_unwatermarked) or len(ids)<n_real:
        raise ValueError('insufficient baseline inputs')
    for kind,n in [('watermarked',n_watermarked),('unwatermarked',n_unwatermarked),('real',n_real)]:
        for i in range(n):
            key=dict(protocol=PROTOCOL,scheme=harness.scheme,stage='baseline',attack='',
                     image_id=str(ids[i]) if kind=='real' else f'prompt{i:04d}',kind=kind,step=0)
            old=log.get(**key)
            if old:
                verify_artifact(root,old)
                continue
            seed=261+i+(100000 if kind=='unwatermarked' else 0)
            image=load_cover(ids[i]) if kind=='real' else harness.generate(prompts[i],seed,kind=='watermarked')
            relative=f'images/{harness.scheme}/baseline/{kind}_{i:04d}.png'
            log.append(measurement(harness,image,key,root,relative,seed=seed))


def removal(image,attack,seed,purifier=None):
    if attack=='jpeg':
        buf=io.BytesIO()
        image.save(buf,format='JPEG',quality=95)
        buf.seek(0)
        return Image.open(buf).convert('RGB')
    if attack=='blur':
        return image.filter(ImageFilter.GaussianBlur(radius=2))
    if attack=='crop':
        width,height=image.size
        side_w,side_h=int(width*.8),int(height*.8)
        left,top=(width-side_w)//2,(height-side_h)//2
        return image.crop((left,top,left+side_w,top+side_h)).resize(image.size,Image.Resampling.LANCZOS)
    if attack=='purification' and purifier is not None:
        import torch
        return purifier(prompt='',image=image,strength=.3,num_inference_steps=50,
                        guidance_scale=7.5,generator=torch.Generator(device=purifier.device).manual_seed(seed)).images[0]
    raise ValueError(f'unsupported removal attack or missing purifier: {attack}')


def run_removals(harness,log,root,purifier=None):
    sources=[r for r in log.rows if r['scheme']==harness.scheme and r['stage']=='baseline' and r['kind']=='watermarked']
    for attack in ATTACKS:
        for source in sources:
            key={k:source[k] for k in KEYS}
            key.update(stage='removal',attack=attack)
            old=log.get(**key)
            if old:
                verify_artifact(root,old)
                continue
            verify_artifact(root,source)
            with Image.open(Path(root)/source['artifact']) as image:
                transformed=removal(image.convert('RGB'),attack,source['seed'],purifier)
            relative=f"images/{harness.scheme}/removal/{attack}_{source['image_id']}.png"
            log.append(measurement(harness,transformed,key,root,relative,seed=source['seed'],source_sha256=source['sha256']))
