"""Pick a torch device that the runners can actually use."""

from __future__ import annotations


def resolve_device(requested: str | None = None) -> str:
    """Return cuda / mps / cpu. Prefer an explicit request when it is available."""
    import torch

    choice = (requested or "").strip().lower() or "auto"
    if choice in {"cuda", "gpu"}:
        if not torch.cuda.is_available():
            raise RuntimeError("requested cuda but torch.cuda.is_available() is False")
        return "cuda"
    if choice == "mps":
        if not getattr(torch.backends, "mps", None) or not torch.backends.mps.is_available():
            raise RuntimeError("requested mps but it is not available")
        return "mps"
    if choice == "cpu":
        return "cpu"
    if choice != "auto":
        raise ValueError(f"unknown device {requested!r}; use auto|cuda|mps|cpu")

    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def empty_cache(device: str | None = None) -> None:
    """Release cached GPU memory when the active device supports it."""
    import gc

    import torch

    gc.collect()
    dev = device or resolve_device("auto")
    if dev == "cuda" and torch.cuda.is_available():
        torch.cuda.empty_cache()
    elif dev == "mps" and getattr(torch.backends, "mps", None):
        try:
            torch.mps.empty_cache()
        except Exception:
            pass
