import pytest
from PIL import Image
from wmforge import benchmark as b
from wmforge.checkin3 import scheme_calibration, single_writer
from wmforge.harness import Detection
from test_benchmark import Fake


def test_calibration_requires_full_baseline_and_separates_prc(tmp_path):
    log = b.BenchmarkLog(tmp_path / "measurements-v2.json")
    with pytest.raises(ValueError, match="incomplete"):
        scheme_calibration(log, "PRC")
    for kind, n, score in [
        ("watermarked", 100, 10.0),
        ("unwatermarked", 200, 0.0),
        ("real", 100, 5.0),
    ]:
        for i in range(n):
            log.append(
                dict(
                    protocol=b.PROTOCOL,
                    scheme="PRC",
                    stage="baseline",
                    attack="",
                    image_id=str(i),
                    kind=kind,
                    step=0,
                    score=score,
                    native=(kind == "watermarked"),
                )
            )
    result = scheme_calibration(log, "PRC")
    assert result["included"] and result["threshold"] == 0
    assert result["calibrated_test"] == "PRC score-only calibrated test"
    assert all("calibrated" not in r for r in log.rows)
    log.rows[0]["native"] = False
    for r in log.rows[1:11]:
        r["native"] = False
    assert not scheme_calibration(log, "PRC")["included"]


def test_single_writer_lock(tmp_path):
    with single_writer(tmp_path):
        with pytest.raises(RuntimeError, match="another worker"):
            with single_writer(tmp_path):
                pass
    with single_writer(tmp_path):
        pass


def test_removals_include_native_initial_misses_and_do_not_duplicate(tmp_path):
    class Miss(Fake):
        def detect(self, image):
            return Detection(0.0, 0.0, False)

    log = b.BenchmarkLog(tmp_path / "measurements-v2.json")
    b.run_baselines(
        Miss(),
        ["a", "b"],
        [1, 2],
        lambda _: Image.new("RGB", (512, 512)),
        log,
        tmp_path,
        n_watermarked=2,
        n_unwatermarked=2,
        n_real=2,
    )

    class Purifier:
        def edit(self, image, prompt=None):
            assert prompt == ""
            return image

    b.run_removals(Miss(), log, tmp_path, Purifier())
    b.run_removals(Miss(), log, tmp_path, Purifier())
    assert sum(r["stage"] == "removal" for r in log.rows) == 8
    assert all(not r["native"] for r in log.rows)
    artifact = tmp_path / log.rows[0]["artifact"]
    artifact.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="modified"):
        b.run_baselines(
            Miss(), ["a", "b"], [1, 2], lambda _: None, log, tmp_path, 2, 2, 2
        )


def test_reference_provenance_survives_interrupt_and_rejects_changed_pixels(tmp_path):
    from wmforge.checkin3 import reference_record

    calls = []

    class Target(Fake):
        def generate(self, *args, **kwargs):
            calls.append(1)
            return super().generate(*args, **kwargs)

    path = "images/PRC/reference.png"
    image = reference_record(Target(), tmp_path, path, "1", "prompt", 10000)
    assert len(calls) == 1
    assert (
        reference_record(Target(), tmp_path, path, "1", "prompt", 10000).tobytes()
        == image.tobytes()
    )
    assert len(calls) == 1
    Image.new("RGB", (512, 512), "blue").save(tmp_path / path)
    with pytest.raises(ValueError, match="reference"):
        reference_record(Target(), tmp_path, path, "1", "prompt", 10000)
    with pytest.raises(ValueError, match="identity"):
        reference_record(Target(), tmp_path, path, "1", "different prompt", 10000)
