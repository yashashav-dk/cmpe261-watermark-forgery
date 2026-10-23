from types import SimpleNamespace
from wmforge.key_state import dump_watermark, load_watermark


def test_key_state_roundtrip_rebinds_pipeline_and_preserves_private_state():
    old=SimpleNamespace(unet=object(),scheduler=object())
    wm=SimpleNamespace(config=SimpleNamespace(pipe=old,scheduler=old.scheduler),
                       key=b'private-key',decoder=SimpleNamespace(matrix=[[1,0],[0,1]]))
    payload=dump_watermark(wm,old)
    new=SimpleNamespace(unet=object(),scheduler=object())
    restored=load_watermark(payload,new)
    assert restored.config.pipe is new
    assert restored.config.scheduler is new.scheduler
    assert restored.key==wm.key and restored.decoder.matrix==wm.decoder.matrix
