"""Build a needle-in-a-haystack payload sized to fill part of a model's context window.

How a payload is put together:

1. Work out the budget. The usable window is the model's context minus the tokens kept
   free for the answer and the system prompt. A fill level of 0.5 targets half of it.
2. Measure the fixed part: the document wrapper, the needles, and the question block.
   Whatever is left of the target is for filler.
3. Draw filler paragraphs from a random generator seeded by the set, adding them until
   the next one would overshoot. The same seed always gives the same paragraphs, and a
   smaller level gets a prefix of a larger level's filler.
4. Slot each needle in between paragraphs at the point nearest its depth.
5. Count the assembled prompt once more (tokens are not exactly additive across
   paragraph joins) and drop trailing filler if it ended up over the target.

Nothing here touches the network or the clock, so the SHA-256 of a payload depends only
on the set, the profile, the level, and the counter.
"""

import hashlib
import math
import random

from langchaingov.golden import filler
from langchaingov.golden.loader import GoldenSetError
from langchaingov.golden.models import GoldenSet, ModelProfile, Needle, Payload
from langchaingov.golden.tokens import TokenCounter

SEPARATOR = "\n\n"
TOLERANCE = 0.01
"""A payload may end up this fraction over its target before trailing filler is dropped."""


def usable_tokens(golden: GoldenSet, profile: ModelProfile, counter: TokenCounter) -> int:
    """Tokens available for the user message: context minus answer reserve and system."""
    return profile.context_tokens - golden.output_reserve_tokens - counter.count(golden.system)


def case_id(level: float) -> str:
    return f"L{round(level * 100):03d}"


def build_payload(
    golden: GoldenSet, profile: ModelProfile, level: float, counter: TokenCounter
) -> Payload:
    if not 0.0 < level <= 1.0:
        raise GoldenSetError(f"fill level {level} is outside (0, 1]")
    target = math.floor(level * usable_tokens(golden, profile, counter))

    # Step 2: what the needles and questions cost on their own.
    fixed = counter.count(_assemble([], golden)[0])
    filler_target = target - fixed
    if filler_target <= 0:
        raise GoldenSetError(
            f"level {level} of a {profile.context_tokens}-token context leaves {target} tokens, "
            f"not enough for the needles and questions ({fixed} tokens)"
        )

    # Step 3: add seeded filler paragraphs up to the target.
    rng = random.Random(golden.seed)
    separator_tokens = counter.count(SEPARATOR)
    paragraphs: list[str] = []
    total = 0
    while True:
        candidate = filler.paragraph(rng)
        cost = counter.count(candidate) + separator_tokens
        if paragraphs and total + cost > filler_target:
            break
        paragraphs.append(candidate)
        total += cost

    # Steps 4 and 5: place needles, recount, trim if the joins pushed it over.
    prompt, depths = _assemble(paragraphs, golden)
    est = counter.count(prompt)
    while est > target * (1 + TOLERANCE) and len(paragraphs) > 1:
        paragraphs.pop()
        prompt, depths = _assemble(paragraphs, golden)
        est = counter.count(prompt)

    return Payload(
        case_id=case_id(level),
        level=level,
        target_tokens=target,
        est_tokens=est,
        chars=len(prompt),
        sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        needle_depths=depths,
        paragraphs=len(paragraphs),
        prompt=prompt,
    )


def question_block(golden: GoldenSet) -> str:
    lines = [f"{needle.id}: {needle.question}" for needle in golden.needles]
    return golden.instruction.strip() + SEPARATOR + "\n".join(lines)


def _assemble(paragraphs: list[str], golden: GoldenSet) -> tuple[str, dict[str, float]]:
    """The full prompt, and where each needle landed as a fraction of the document."""
    slots: dict[int, list[Needle]] = {}
    for needle in sorted(golden.needles, key=lambda n: n.depth):
        slots.setdefault(round(needle.depth * len(paragraphs)), []).append(needle)

    blocks: list[str] = []
    offsets: dict[str, int] = {}
    position = 0
    for index in range(len(paragraphs) + 1):
        for needle in slots.get(index, []):
            offsets[needle.id] = position
            blocks.append(needle.fact)
            position += len(needle.fact) + len(SEPARATOR)
        if index < len(paragraphs):
            blocks.append(paragraphs[index])
            position += len(paragraphs[index]) + len(SEPARATOR)

    document = SEPARATOR.join(blocks)
    depths = {nid: round(offset / max(len(document), 1), 4) for nid, offset in offsets.items()}
    prompt = f"<document>\n{document}\n</document>{SEPARATOR}{question_block(golden)}"
    return prompt, depths
