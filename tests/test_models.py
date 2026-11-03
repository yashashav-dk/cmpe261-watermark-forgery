from wmforge.models import CONDITIONS, describe, provider, resolve_attacker


def test_c1_and_c2_are_pinned_and_distinct():
    c1 = resolve_attacker("C1")
    c2 = resolve_attacker("C2")
    assert c1.model_id != c2.model_id
    assert c1.revision != c2.revision
    assert provider().model_id == c1.model_id
    assert set(CONDITIONS) == {"C1", "C2"}
    assert describe("C2")["condition"] == "C2"


def test_unknown_condition_rejected():
    import pytest

    with pytest.raises(ValueError):
        resolve_attacker("C9")
