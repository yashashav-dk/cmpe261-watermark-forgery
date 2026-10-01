import pytest
from PIL import Image

from wmforge.harness import Detection, Harness, parse_detection


class FakeConfig:
    gen_seed = 0
    init_latents = None


class FakeWatermark:
    def __init__(self, result):
        self.config = FakeConfig()
        self.result = result
        self.calls = []

    def generate_watermarked_media(self, prompt):
        self.calls.append(("watermarked", prompt, self.config.gen_seed, self.config.init_latents))
        return Image.new("RGB", (8, 8))

    def generate_unwatermarked_media(self, prompt):
        self.calls.append(("unwatermarked", prompt, self.config.gen_seed, self.config.init_latents))
        return Image.new("RGB", (8, 8))

    def detect_watermark_in_media(self, image, **kwargs):
        self.calls.append(("detect", kwargs))
        return self.result


def test_parse_detection_lower_is_watermarked():
    detection = parse_detection("TR", {"is_watermarked": True, "l1_distance": 12.5})
    assert detection == Detection(raw_score=12.5, score=-12.5, is_watermarked=True)


def test_parse_detection_higher_is_watermarked():
    detection = parse_detection("GS", {"is_watermarked": False, "bit_acc": 0.52})
    assert detection == Detection(raw_score=0.52, score=0.52, is_watermarked=False)


def test_parse_detection_unknown_scheme():
    with pytest.raises(ValueError, match="unknown scheme 'XX'"):
        parse_detection("XX", {"is_watermarked": True})


def test_parse_detection_missing_key():
    with pytest.raises(ValueError, match="bit_acc"):
        parse_detection("GS", {"is_watermarked": True, "l1_distance": 3.0})


def test_parse_detection_non_finite():
    with pytest.raises(ValueError, match="not finite"):
        parse_detection("TR", {"is_watermarked": False, "l1_distance": float("nan")})


def test_generate_reseeds_and_routes():
    watermark = FakeWatermark({"is_watermarked": True, "l1_distance": 1.0})
    harness = Harness("TR", watermark, latent_sampler=lambda seed: f"latents-{seed}")
    harness.generate("a cat", seed=7, watermarked=True)
    harness.generate("a cat", seed=8, watermarked=False)
    assert watermark.calls == [
        ("watermarked", "a cat", 7, "latents-7"),
        ("unwatermarked", "a cat", 8, "latents-8"),
    ]


def test_detect_uses_toolkit_default_call():
    watermark = FakeWatermark({"is_watermarked": True, "l1_distance": 1.0})
    harness = Harness("TR", watermark, latent_sampler=lambda seed: None)
    assert harness.detect(Image.new("RGB", (8, 8))).is_watermarked is True
    assert watermark.calls == [("detect", {})]


def test_detect_passes_guidance_override():
    watermark = FakeWatermark({"is_watermarked": True, "bit_acc": 0.9})
    harness = Harness("GS", watermark, latent_sampler=lambda seed: None, detect_guidance_scale=1.0)
    harness.detect(Image.new("RGB", (8, 8)))
    assert watermark.calls == [("detect", {"guidance_scale": 1.0})]
