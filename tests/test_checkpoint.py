import pytest
import torch
from PIL import Image
from wmforge import imprint


@pytest.fixture
def toy(monkeypatch):
    monkeypatch.setattr(imprint,'_empty_prompt_embeds',lambda _:None)
    monkeypatch.setattr(imprint,'encode',lambda _,image:torch.tensor([float(image.getpixel((0,0))[0])/255]))
    monkeypatch.setattr(imprint,'invert',lambda _,z,embeds,differentiable=False:z*2)
    monkeypatch.setattr(imprint,'decode',lambda _,z:Image.new('RGB',(8,8),(int(z.detach().clamp(0,1).item()*255),0,0)))
    return Image.new('RGB',(8,8)),Image.new('RGB',(8,8),'white')


@pytest.mark.parametrize('publication',['before_log','after_log'])
def test_resume_matches_optimizer_trajectory_and_measurement(tmp_path,toy,publication):
    cover,reference=toy
    expected=[]
    imprint.imprint(cover,reference,None,max_steps=6,validate_every=2,
                    on_validate=lambda s,i,t:expected.append(i.tobytes()) or False)
    path=tmp_path/'checkpoint.pt'
    rows=[]
    def measure(step,image,seconds):
        return {'step':step,'pixels':image.tobytes().hex()}
    def publish(row,image):
        if publication=='after_log': rows.append(row)
        raise RuntimeError('interruption')
    with pytest.raises(RuntimeError,match='interruption'):
        imprint.imprint(cover,reference,None,max_steps=6,validate_every=2,
                       checkpoint_path=path,measure=measure,publish=publish)
    snapshot=torch.load(path,weights_only=False)
    assert snapshot['step']==2 and snapshot['optimizer']['state']
    def recovered(row,image):
        if row not in rows: rows.append(row)
        assert image.tobytes().hex()==row['pixels']
    result=imprint.imprint(cover,reference,None,max_steps=6,validate_every=2,
                          checkpoint_path=path,measure=measure,publish=recovered)
    assert result.steps_run==6
    assert len(rows)==3
    assert [bytes.fromhex(row['pixels']) for row in rows]==expected
    with pytest.raises(ValueError,match='settings'):
        imprint.imprint(cover,reference,None,max_steps=8,validate_every=2,
                        checkpoint_path=path,measure=measure,publish=recovered)
