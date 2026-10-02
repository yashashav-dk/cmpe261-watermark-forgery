import csv
from types import SimpleNamespace

import pytest
from PIL import Image

from wmforge import smoke
from wmforge.harness import Detection
from wmforge.records import RunLog

META = smoke.RunMeta(target_rev="target123", attacker_rev="attacker456")


class FakeHarness:
    """Flags an image as watermarked when any channel of its first pixel is at least 200."""

    scheme = "TR"

    def __init__(self):
        self.generated = []

    def generate(self, prompt, seed, watermarked):
        self.generated.append((prompt, seed, watermarked))
        return Image.new("RGB", (16, 16), (200, 0, 0) if watermarked else (0, 0, 0))

    def detect(self, image):
        brightest = max(image.getpixel((0, 0)))
        return Detection(raw_score=float(brightest), score=float(brightest), is_watermarked=brightest >= 200)


class FakeImprint:
    """Produces a detectable image from step 20 on."""

    def __init__(self):
        self.calls = 0

    def __call__(self, cover, reference, attacker, max_steps, validate_every, on_validate):
        self.calls += 1
        records = []
        image = cover
        for step in range(validate_every, max_steps + 1, validate_every):
            records.append(SimpleNamespace(step=step, loss=1.0 / step, seconds=0.5))
            image = Image.new("RGB", cover.size, (0, 220, 0) if step >= 20 else (50, 50, 50))
            if on_validate(step, image, 0.5 * step):
                return SimpleNamespace(image=image, steps_run=step, records=records, stopped_early=True)
        return SimpleNamespace(image=image, steps_run=max_steps, records=records, stopped_early=False)


def _cover(image_id):
    return Image.new("RGB", (16, 16), (10, 10, 10))


def _quality(cover, image):
    return {"psnr": 30.0, "ssim": 0.9, "lpips": 0.1}


def _rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_run_clean_writes_both_kinds(tmp_path):
    log = RunLog(tmp_path / "runs.csv")
    smoke.run_clean(FakeHarness(), ["a cat", "a dog"], log, META)
    rows = _rows(tmp_path / "runs.csv")
    assert [(r["image_id"], r["kind"], r["is_watermarked"]) for r in rows] == [
        ("prompt0000", "watermarked", "1"),
        ("prompt0000", "unwatermarked", "0"),
        ("prompt0001", "watermarked", "1"),
        ("prompt0001", "unwatermarked", "0"),
    ]
    assert rows[0]["seed"] == "0" and rows[2]["seed"] == "1"
    assert rows[0]["target_rev"] == "target123"
    assert float(rows[0]["seconds"]) >= 0


def test_run_clean_resumes(tmp_path):
    path = tmp_path / "runs.csv"
    smoke.run_clean(FakeHarness(), ["a cat"], RunLog(path), META)
    second = FakeHarness()
    smoke.run_clean(second, ["a cat", "a dog"], RunLog(path), META)
    assert [call[0] for call in second.generated] == ["a dog", "a dog"]
    assert len(_rows(path)) == 4


def test_run_real_records_each_photo(tmp_path):
    log = RunLog(tmp_path / "runs.csv")
    smoke.run_real(FakeHarness(), [39769, 139], _cover, log, META)
    rows = _rows(tmp_path / "runs.csv")
    assert [(r["stage"], r["image_id"], r["kind"], r["is_watermarked"]) for r in rows] == [
        ("real", "39769", "real", "0"),
        ("real", "139", "real", "0"),
    ]


def test_run_imprint_stops_at_first_detection(tmp_path):
    log = RunLog(tmp_path / "runs.csv")
    fake_imprint = FakeImprint()
    smoke.run_imprint(
        FakeHarness(), object(), [39769], ["a cat"], _cover, log, META, tmp_path / "images", fake_imprint, _quality
    )
    rows = _rows(tmp_path / "runs.csv")
    assert [(r["kind"], r["step"], r["is_watermarked"]) for r in rows] == [
        ("reference", "0", "1"),
        ("forged", "10", "0"),
        ("forged", "20", "1"),
        ("done", "0", "1"),
    ]
    forged = rows[2]
    assert (forged["attack"], forged["condition"], forged["psnr"], forged["seconds"]) == ("imprint", "C1", "30.0", "10.0")
    assert forged["attacker_rev"] == "attacker456"
    for part in ("cover", "reference", "forged"):
        assert (tmp_path / "images" / f"TR_39769_{part}.png").exists()


def test_run_imprint_runs_to_cap_without_early_stop(tmp_path):
    log = RunLog(tmp_path / "runs.csv")
    smoke.run_imprint(
        FakeHarness(),
        object(),
        [39769],
        ["a cat"],
        _cover,
        log,
        META,
        tmp_path / "images",
        FakeImprint(),
        _quality,
        max_steps=40,
        stop_on_detect=False,
    )
    forged_steps = [r["step"] for r in _rows(tmp_path / "runs.csv") if r["kind"] == "forged"]
    assert forged_steps == ["10", "20", "30", "40"]


def test_run_imprint_skips_finished_cover(tmp_path):
    path = tmp_path / "runs.csv"
    fake_imprint = FakeImprint()
    arguments = (object(), [39769], ["a cat"], _cover)
    smoke.run_imprint(FakeHarness(), *arguments, RunLog(path), META, tmp_path / "images", fake_imprint, _quality)
    smoke.run_imprint(FakeHarness(), *arguments, RunLog(path), META, tmp_path / "images", fake_imprint, _quality)
    assert fake_imprint.calls == 1
    assert len(_rows(path)) == 4


def test_run_imprint_needs_a_prompt_per_cover(tmp_path):
    log = RunLog(tmp_path / "runs.csv")
    with pytest.raises(ValueError, match="2 covers but only 1 prompts"):
        smoke.run_imprint(
            FakeHarness(), object(), [1, 2], ["a cat"], _cover, log, META, tmp_path / "images", FakeImprint(), _quality
        )


def test_run_imprint_resume_follows_logged_verdicts(tmp_path):
    # An interrupted attempt logged "not flagged" at steps 10 and 20. On the re-run the detector
    # would flag step 20, but the log must stay the single record of what was decided.
    path = tmp_path / "runs.csv"
    log = RunLog(path)
    base = dict(stage="imprint", scheme="TR", condition="C1", image_id="39769", attack="imprint")
    log.append({**base, "kind": "reference", "step": 0, "raw_score": 200.0, "score": 200.0, "is_watermarked": 1})
    for step in (10, 20):
        log.append({**base, "kind": "forged", "step": step, "raw_score": 50.0, "score": 50.0, "is_watermarked": 0})

    smoke.run_imprint(
        FakeHarness(), object(), [39769], ["a cat"], _cover, RunLog(path), META, tmp_path / "images", FakeImprint(), _quality
    )
    rows = [(r["kind"], r["step"], r["is_watermarked"]) for r in _rows(path)]
    assert rows == [
        ("reference", "0", "1"),
        ("forged", "10", "0"),
        ("forged", "20", "0"),
        ("forged", "30", "1"),
        ("done", "0", "1"),
    ]
