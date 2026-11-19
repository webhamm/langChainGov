"""Payload generation, sized with the offline CharCounter."""

import hashlib
import math
import random

import pytest

from langchaingov.golden import filler
from langchaingov.golden.generator import build_payload, case_id, usable_tokens
from langchaingov.golden.loader import GoldenSetError, load_set
from langchaingov.golden.models import GoldenSet, ModelProfile, Payload
from langchaingov.golden.tokens import CharCounter

COUNTER = CharCounter()
PROFILE = ModelProfile(name="m", context_tokens=32768, local=True)


@pytest.fixture(scope="module")
def golden() -> GoldenSet:
    return load_set(None)


@pytest.fixture(scope="module")
def ladder(golden: GoldenSet) -> list[Payload]:
    return [build_payload(golden, PROFILE, level, COUNTER) for level in golden.fill_levels]


def max_paragraph_tokens(golden: GoldenSet, payload: Payload) -> int:
    rng = random.Random(golden.seed)
    return max(COUNTER.count(filler.paragraph(rng)) for _ in range(payload.paragraphs + 1))


def test_same_inputs_give_the_same_bytes(golden: GoldenSet, ladder: list[Payload]) -> None:
    again = build_payload(golden, PROFILE, golden.fill_levels[1], COUNTER)
    assert again.sha256 == ladder[1].sha256
    assert again.prompt == ladder[1].prompt


def test_sha256_is_of_the_prompt(ladder: list[Payload]) -> None:
    for payload in ladder:
        assert payload.sha256 == hashlib.sha256(payload.prompt.encode()).hexdigest()
        assert payload.chars == len(payload.prompt)


def test_a_different_seed_gives_different_bytes(golden: GoldenSet, ladder: list[Payload]) -> None:
    reseeded = golden.model_copy(update={"seed": golden.seed + 1})
    assert build_payload(reseeded, PROFILE, 0.5, COUNTER).sha256 != ladder[1].sha256


def test_size_is_within_tolerance_of_target(golden: GoldenSet, ladder: list[Payload]) -> None:
    usable = usable_tokens(golden, PROFILE, COUNTER)
    for payload in ladder:
        assert payload.target_tokens == math.floor(payload.level * usable)
        tolerance = max(
            math.ceil(0.01 * payload.target_tokens), max_paragraph_tokens(golden, payload)
        )
        assert abs(payload.est_tokens - payload.target_tokens) <= tolerance
        assert payload.est_tokens == COUNTER.count(payload.prompt)


def test_size_grows_with_each_level(ladder: list[Payload]) -> None:
    sizes = [p.est_tokens for p in ladder]
    assert sizes == sorted(sizes) and len(set(sizes)) == len(sizes)
    assert [p.case_id for p in ladder] == ["L025", "L050", "L075", "L090"]


def test_needles_appear_once_in_depth_order_near_their_depth(
    golden: GoldenSet, ladder: list[Payload]
) -> None:
    for payload in ladder:
        positions = [payload.prompt.index(n.fact) for n in golden.needles]
        assert positions == sorted(positions)
        for n in golden.needles:
            assert payload.prompt.casefold().count(n.answer.casefold()) == 1
            assert abs(payload.needle_depths[n.id] - n.depth) < 0.03


def test_document_then_instruction_then_questions(golden: GoldenSet, ladder: list[Payload]) -> None:
    prompt = ladder[0].prompt
    assert prompt.startswith("<document>\n")
    _, tail = prompt.split("</document>")
    assert tail.strip().startswith(golden.instruction[:40])
    assert prompt.endswith(f"{golden.needles[-1].id}: {golden.needles[-1].question}")


def test_smaller_levels_reuse_the_same_filler_prefix(ladder: list[Payload]) -> None:
    first_paragraph = ladder[0].prompt.split("\n\n")[0]
    assert all(p.prompt.startswith(first_paragraph) for p in ladder)


@pytest.mark.parametrize("level", [0.0, -0.1, 1.01])
def test_level_out_of_range(golden: GoldenSet, level: float) -> None:
    with pytest.raises(GoldenSetError, match=r"outside \(0, 1\]"):
        build_payload(golden, PROFILE, level, COUNTER)


def test_context_too_small_for_the_needles(golden: GoldenSet) -> None:
    tiny = ModelProfile(name="tiny", context_tokens=1200)
    with pytest.raises(GoldenSetError, match="not enough for the needles"):
        build_payload(golden, tiny, 0.25, COUNTER)


def test_case_id_formats_percent() -> None:
    assert [case_id(x) for x in (0.05, 0.5, 0.9, 1.0)] == ["L005", "L050", "L090", "L100"]
