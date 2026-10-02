import numpy as np
import pytest
from PIL import Image

torch = pytest.importorskip("torch")
diffusers = pytest.importorskip("diffusers")

from wmforge import imprint  # noqa: E402

pytestmark = pytest.mark.slow
TINY_MODEL = "hf-internal-testing/tiny-stable-diffusion-torch"


@pytest.fixture(scope="module")
def attacker():
    pipe = diffusers.StableDiffusionPipeline.from_pretrained(TINY_MODEL, safety_checker=None)
    pipe.set_progress_bar_config(disable=True)
    inverse = diffusers.DDIMInverseScheduler.from_config(pipe.scheduler.config)
    return imprint.make_attacker(pipe, inverse, num_inversion_steps=4)


@pytest.fixture(scope="module")
def side(attacker):
    return attacker.pipe.unet.config.sample_size * attacker.pipe.vae_scale_factor


def _noise_image(side, seed):
    pixels = np.random.default_rng(seed).integers(0, 256, (side, side, 3), dtype=np.uint8)
    return Image.fromarray(pixels)


def test_make_attacker_freezes_weights(attacker):
    assert not any(p.requires_grad for p in attacker.pipe.unet.parameters())
    assert not any(p.requires_grad for p in attacker.pipe.vae.parameters())


def test_encode_decode_keeps_image_size(attacker, side):
    cover = _noise_image(side, 0)
    assert imprint.decode(attacker, imprint.encode(attacker, cover)).size == cover.size


def test_imprint_reduces_loss(attacker, side):
    torch.manual_seed(0)
    result = imprint.imprint(_noise_image(side, 0), _noise_image(side, 1), attacker, max_steps=8)
    assert result.steps_run == 8
    assert [record.step for record in result.records] == list(range(1, 9))
    assert min(record.loss for record in result.records[1:]) < result.records[0].loss
    assert all(record.seconds > 0 for record in result.records)
    assert result.image.size == (side, side)
    assert result.stopped_early is False


def test_on_validate_schedule_and_early_stop(attacker, side):
    seen = []

    def on_validate(step, image, optim_seconds):
        seen.append((step, image.size, optim_seconds > 0))
        return step == 4

    result = imprint.imprint(
        _noise_image(side, 0), _noise_image(side, 1), attacker, max_steps=8, validate_every=2, on_validate=on_validate
    )
    assert seen == [(2, (side, side), True), (4, (side, side), True)]
    assert result.steps_run == 4
    assert result.stopped_early is True


def test_on_validate_called_at_cap(attacker, side):
    steps = []
    imprint.imprint(
        _noise_image(side, 0),
        _noise_image(side, 1),
        attacker,
        max_steps=3,
        validate_every=2,
        on_validate=lambda step, image, seconds: steps.append(step) or False,
    )
    assert steps == [2, 3]


def test_imprint_rejects_bad_arguments(attacker, side):
    cover = _noise_image(side, 0)
    with pytest.raises(ValueError, match="sizes differ"):
        imprint.imprint(cover, _noise_image(side * 2, 1), attacker, max_steps=1)
    with pytest.raises(ValueError, match="max_steps"):
        imprint.imprint(cover, cover, attacker, max_steps=0)
    with pytest.raises(ValueError, match="validate_every"):
        imprint.imprint(cover, cover, attacker, max_steps=1, validate_every=0)
