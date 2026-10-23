import pytest
import torch
from PIL import Image
from wmforge import imprint


@pytest.fixture
def toy(monkeypatch):
    monkeypatch.setattr(imprint, "_empty_prompt_embeds", lambda _: None)
    monkeypatch.setattr(
        imprint,
        "encode",
        lambda _, image: torch.tensor([float(image.getpixel((0, 0))[0]) / 255]),
    )
    monkeypatch.setattr(
        imprint, "invert", lambda _, z, embeds, differentiable=False: z * 2
    )
    monkeypatch.setattr(
        imprint,
        "decode",
        lambda _, z: Image.new(
            "RGB", (8, 8), (int(z.detach().clamp(0, 1).item() * 255), 0, 0)
        ),
    )
    return Image.new("RGB", (8, 8)), Image.new("RGB", (8, 8), "white")


@pytest.mark.parametrize("publication", ["before_log", "after_log"])
def test_resume_matches_optimizer_trajectory_and_measurement(
    tmp_path, toy, publication
):
    cover, reference = toy
    expected = []
    imprint.imprint(
        cover,
        reference,
        None,
        max_steps=6,
        validate_every=2,
        on_validate=lambda s, i, t: expected.append(i.tobytes()) or False,
    )
    path = tmp_path / "checkpoint.pt"
    rows = []

    def measure(step, image, seconds):
        return {"step": step, "pixels": image.tobytes().hex()}

    def publish(row, image):
        if publication == "after_log":
            rows.append(row)
        raise RuntimeError("interruption")

    with pytest.raises(RuntimeError, match="interruption"):
        imprint.imprint(
            cover,
            reference,
            None,
            max_steps=6,
            validate_every=2,
            checkpoint_path=path,
            measure=measure,
            publish=publish,
        )
    snapshot = torch.load(path, weights_only=False)
    assert snapshot["step"] == 2 and snapshot["optimizer"]["state"]

    def recovered(row, image):
        if row not in rows:
            rows.append(row)
        assert image.tobytes().hex() == row["pixels"]

    result = imprint.imprint(
        cover,
        reference,
        None,
        max_steps=6,
        validate_every=2,
        checkpoint_path=path,
        measure=measure,
        publish=recovered,
    )
    assert result.steps_run == 6
    assert len(rows) == 3
    assert [bytes.fromhex(row["pixels"]) for row in rows] == expected
    with pytest.raises(ValueError, match="settings"):
        imprint.imprint(
            cover,
            reference,
            None,
            max_steps=8,
            validate_every=2,
            checkpoint_path=path,
            measure=measure,
            publish=recovered,
        )


def test_imprint_times_synchronized_work(toy, monkeypatch):
    calls = []
    monkeypatch.setattr(
        imprint, "_synchronize", lambda device: calls.append(device.type)
    )
    imprint.imprint(*toy, None, max_steps=2)
    assert calls == ["cpu", "cpu", "cpu", "cpu"]


@pytest.mark.parametrize(
    "failure_point", ["before_checkpoint", "before_image", "after_image", "after_log"]
)
def test_recovery_preserves_random_trajectory_across_publication_boundaries(
    tmp_path, toy, monkeypatch, failure_point
):
    import random
    import numpy as np

    monkeypatch.setattr(
        imprint,
        "invert",
        lambda _, z, embeds, differentiable=False: z * 2 + torch.rand_like(z) * 0.01,
    )
    cover, reference = toy

    def seed():
        torch.manual_seed(261)
        random.seed(261)
        np.random.seed(261)

    def measure(step, image, seconds):
        return {
            "step": step,
            "pixels": image.tobytes().hex(),
            "python": random.random(),
            "numpy": float(np.random.rand()),
        }

    def simulate(root, interrupt):
        rows = []

        def measured(step, image, seconds):
            row = measure(step, image, seconds)
            if interrupt and step == 4 and failure_point == "before_checkpoint":
                raise RuntimeError("interrupted")
            return row

        def publish(row, image):
            if interrupt and row["step"] == 4 and failure_point == "before_image":
                raise RuntimeError("interrupted")
            image.save(root / f"step{row['step']}.png")
            if interrupt and row["step"] == 4 and failure_point == "after_image":
                raise RuntimeError("interrupted")
            if row not in rows:
                rows.append(row)
            if interrupt and row["step"] == 4 and failure_point == "after_log":
                raise RuntimeError("interrupted")

        return rows, measured, publish

    full = tmp_path / "full"
    full.mkdir()
    seed()
    expected, measure_full, publish_full = simulate(full, False)
    imprint.imprint(
        cover,
        reference,
        None,
        max_steps=6,
        validate_every=2,
        checkpoint_path=full / "checkpoint.pt",
        measure=measure_full,
        publish=publish_full,
    )
    broken = tmp_path / "broken"
    broken.mkdir()
    seed()
    actual, measure_broken, publish_broken = simulate(broken, True)
    with pytest.raises(RuntimeError, match="interrupted"):
        imprint.imprint(
            cover,
            reference,
            None,
            max_steps=6,
            validate_every=2,
            checkpoint_path=broken / "checkpoint.pt",
            measure=measure_broken,
            publish=publish_broken,
        )
    torch.manual_seed(999)
    random.seed(999)
    np.random.seed(999)

    def recovered(row, image):
        image.save(broken / f"step{row['step']}.png")
        if row not in actual:
            actual.append(row)

    imprint.imprint(
        cover,
        reference,
        None,
        max_steps=6,
        validate_every=2,
        checkpoint_path=broken / "checkpoint.pt",
        measure=measure,
        publish=recovered,
    )
    assert actual == expected
    for row in actual:
        with Image.open(broken / f"step{row['step']}.png") as saved:
            assert saved.tobytes().hex() == row["pixels"]
    checkpoint_full = torch.load(full / "checkpoint.pt", weights_only=False)
    checkpoint_resumed = torch.load(broken / "checkpoint.pt", weights_only=False)
    assert torch.equal(checkpoint_full["latent"], checkpoint_resumed["latent"])
    assert torch.equal(checkpoint_full["torch_rng"], checkpoint_resumed["torch_rng"])
