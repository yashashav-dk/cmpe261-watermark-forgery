import json
import pytest
from PIL import Image
from wmforge.benchmark import calibrate, extend_selection, BenchmarkLog, bind_manifest, run_baselines, removal, budget_rows
from wmforge.harness import Detection


def row(attack='jpeg'):
    return dict(protocol='checkin3-v2', scheme='TR', stage='removal', attack=attack,
                image_id='0', kind='watermarked', step=0, score=1., native=True)


def test_threshold_strict_ties_and_resolution():
    assert calibrate(list(range(200))) == 197
    scores=[0.]*196 + [1.]*4
    threshold=calibrate(scores)
    assert threshold == 1 and sum(s>threshold for s in scores)==0
    with pytest.raises(ValueError): calibrate([0.]*199)
    with pytest.raises(ValueError): calibrate([float('nan')]*200)


def test_prefix_preserved_and_extension_deterministic():
    assert extend_selection([8,2], range(20), 8)[:2] == [8,2]
    assert extend_selection([8,2], range(20), 8) == extend_selection([8,2], reversed(range(20)), 8)
    with pytest.raises(ValueError): extend_selection([1], [1,2], 3)


def test_versioned_log_attack_keys_and_immutable_duplicates(tmp_path):
    log=BenchmarkLog(tmp_path/'measurements-v2.json')
    log.append(row()); log.append(row('blur')); log.append(row())
    assert len(BenchmarkLog(log.path).rows)==2
    with pytest.raises(ValueError): log.append(dict(row(),score=2))
    assert json.loads(log.path.read_text())['schema_version']==2


def test_manifest_rejects_changed_identity(tmp_path):
    bind_manifest(tmp_path/'manifest.json', {'seed':261, 'inputs':['a']})
    bind_manifest(tmp_path/'manifest.json', {'seed':261, 'inputs':['a']})
    with pytest.raises(ValueError): bind_manifest(tmp_path/'manifest.json', {'seed':262})


class Fake:
    scheme='PRC'
    def generate(self,prompt,seed,watermarked):
        return Image.new('RGB',(512,512),(255 if watermarked else 0,seed%256,0))
    def detect(self,image):
        return Detection(1.,1.,bool(image.getpixel((0,0))[0]))


def test_independent_counts_and_saved_artifacts(tmp_path):
    log=BenchmarkLog(tmp_path/'measurements-v2.json')
    run_baselines(Fake(), ['x']*5, [1,2], lambda _: Image.new('RGB',(512,512)),
                  log,tmp_path, n_watermarked=2,n_unwatermarked=5,n_real=2)
    assert [sum(r['kind']==k for r in log.rows) for k in ['watermarked','unwatermarked','real']]==[2,5,2]
    for r in log.rows:
        assert (tmp_path/r['artifact']).is_file()
        assert 'native' in r and 'calibrated' not in r


def test_budget_decision_uses_exact_step_not_ever_detected():
    rows=[dict(row(),stage='imprint',step=s,native=v) for s,v in [(10,True),(50,False),(100,True),(150,False)]]
    assert [r['native'] for r in budget_rows(rows,50)]==[False]
    assert [r['native'] for r in budget_rows(rows,150)]==[False]


@pytest.mark.parametrize('attack',['jpeg','blur','crop'])
def test_removals_keep_dimensions(attack):
    image=Image.new('RGB',(512,512),'red')
    assert removal(image,attack,261).size==(512,512)
