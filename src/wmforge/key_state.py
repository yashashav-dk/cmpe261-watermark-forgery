"""Persist complete toolkit state while rebinding shared pipeline components."""
from __future__ import annotations

import io
import pickle
from pathlib import Path

from wmforge.benchmark import atomic_bytes


def bindings(pipe):
    result={'pipe':pipe}
    for name in ('scheduler','unet','vae','text_encoder','tokenizer','safety_checker','feature_extractor'):
        value=getattr(pipe,name,None)
        if value is not None:
            result[name]=value
    return result


def dump_watermark(watermark,pipe):
    objects=bindings(pipe)
    class Writer(pickle.Pickler):
        def persistent_id(self,obj):
            return next((name for name,value in objects.items() if obj is value),None)
    buffer=io.BytesIO()
    Writer(buffer,protocol=5).dump(watermark)
    return buffer.getvalue()


def load_watermark(payload,pipe):
    objects=bindings(pipe)
    class Reader(pickle.Unpickler):
        def persistent_load(self,name):
            if name not in objects:
                raise ValueError(f'unknown pipeline binding: {name}')
            return objects[name]
    return Reader(io.BytesIO(payload)).load()


def restore_or_save(harness,pipe,path):
    """Use only trusted local run files; pickle state includes toolkit key objects."""
    path=Path(path)
    if path.exists():
        harness.watermark=load_watermark(path.read_bytes(),pipe)
    else:
        atomic_bytes(path,dump_watermark(harness.watermark,pipe))
        harness.watermark=load_watermark(path.read_bytes(),pipe)
    return harness
