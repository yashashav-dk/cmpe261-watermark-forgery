"""Pinned models for the provider and for each attacker-model condition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModelSpec:
    condition: str
    role: str
    model_id: str
    revision: str
    notes: str


# Provider / C1 attacker: same pinned community mirror used since Check-in 1.
TARGET = ModelSpec(
    condition="C1",
    role="provider_and_same_model_attacker",
    model_id="Manojb/stable-diffusion-2-1-base",
    revision="0094d483a120f3f33dafbd187ea4aa60d10de75c",
    notes="Stable Diffusion 2.1-base community mirror; fp32, 512x512",
)

# C2 attacker: same architecture family, different weights (project-spec T1).
ATTACKER_C2 = ModelSpec(
    condition="C2",
    role="cross_weight_attacker",
    model_id="stable-diffusion-v1-5/stable-diffusion-v1-5",
    revision="451f4fe16113bdc1c2ae000260dc525a8138637d",
    notes="Stable Diffusion 1.5; used only as the imprint attacker",
)

CONDITIONS = {
    "C1": TARGET,
    "C2": ATTACKER_C2,
}


def resolve_attacker(condition: str) -> ModelSpec:
    if condition not in CONDITIONS:
        raise ValueError(
            f"unknown attacker condition {condition!r}; known: {sorted(CONDITIONS)}"
        )
    return CONDITIONS[condition]


def provider() -> ModelSpec:
    return TARGET


def describe(condition: Optional[str] = None) -> dict:
    if condition is None:
        return {name: spec.__dict__ for name, spec in CONDITIONS.items()}
    return resolve_attacker(condition).__dict__
