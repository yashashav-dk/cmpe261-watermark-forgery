import pytest

from wmforge.device import empty_cache, resolve_device


def test_resolve_device_auto_returns_known_label():
    device = resolve_device("auto")
    assert device in {"cuda", "mps", "cpu"}


def test_resolve_device_cpu_always_works():
    assert resolve_device("cpu") == "cpu"


def test_resolve_device_rejects_unknown():
    with pytest.raises(ValueError):
        resolve_device("tpu")


def test_empty_cache_cpu_does_not_crash():
    empty_cache("cpu")
