import io

import pytest
import requests
from PIL import Image

from wmforge import data


def _jpeg_bytes(size=(640, 480), mode="RGB"):
    buffer = io.BytesIO()
    Image.new(mode, size, 128).save(buffer, format="JPEG")
    return buffer.getvalue()


class _Response:
    def __init__(self, content=b"", error=None):
        self.content = content
        self._error = error

    def raise_for_status(self):
        if self._error:
            raise self._error


def test_select_prompts_is_deterministic():
    pool = [f"prompt {i}" for i in range(100)]
    assert data.select_prompts(pool, 10, seed=261) == data.select_prompts(pool, 10, seed=261)
    assert data.select_prompts(pool, 10, seed=261) != data.select_prompts(pool, 10, seed=262)


def test_select_prompts_normalizes_whitespace_and_dedupes():
    pool = ["a cat\non a  mat", "a cat on a mat", "", "   ", None, "a dog"]
    chosen = data.select_prompts(pool, 2, seed=0)
    assert sorted(chosen) == ["a cat on a mat", "a dog"]
    assert all("\n" not in prompt for prompt in chosen)


def test_select_prompts_rejects_oversized_request():
    with pytest.raises(ValueError, match="only 1 unique"):
        data.select_prompts(["one", "one"], 2, seed=0)


def test_select_image_ids_dedupes_and_is_deterministic():
    ids = [3, 1, 2, 2, 3]
    assert sorted(data.select_image_ids(ids, 3, seed=0)) == [1, 2, 3]
    assert data.select_image_ids(range(100), 5, seed=261) == data.select_image_ids(range(100), 5, seed=261)
    with pytest.raises(ValueError):
        data.select_image_ids(ids, 4, seed=0)


def test_write_and_read_lines_roundtrip(tmp_path):
    path = tmp_path / "nested" / "items.txt"
    data.write_lines(path, ["alpha", "beta"])
    assert data.read_lines(path) == ["alpha", "beta"]
    data.write_lines(path, [39769, 139])
    assert data.read_image_ids(path) == [39769, 139]


def test_coco_url_zero_pads():
    assert data.coco_url(39769) == "http://images.cocodataset.org/val2017/000000039769.jpg"


def test_center_crop_resize_grayscale_wide():
    out = data.center_crop_resize(Image.new("L", (640, 480), 200))
    assert out.size == (512, 512)
    assert out.mode == "RGB"


def test_center_crop_resize_tall_keeps_centre():
    image = Image.new("RGB", (100, 300), (0, 0, 0))
    image.paste((255, 255, 255), (0, 100, 100, 200))
    out = data.center_crop_resize(image, size=64)
    assert out.size == (64, 64)
    assert out.getpixel((32, 32)) == (255, 255, 255)


def test_load_cover_downloads_once(tmp_path, monkeypatch):
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return _Response(_jpeg_bytes())

    monkeypatch.setattr(data.requests, "get", fake_get)
    first = data.load_cover(39769, tmp_path)
    second = data.load_cover(39769, tmp_path)
    assert first.size == second.size == (512, 512)
    assert calls == [data.coco_url(39769)]


def test_load_cover_http_error_leaves_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        data.requests, "get", lambda url, timeout: _Response(error=requests.HTTPError("404"))
    )
    with pytest.raises(requests.HTTPError):
        data.load_cover(1, tmp_path)
    assert list(tmp_path.iterdir()) == []
