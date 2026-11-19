"""Word lists and sentence templates for the golden set's filler text.

The filler reads like a fictional harbour-survey log: plausible prose for the model to
read past, with no real people or places. Nothing here may contain a needle's answer.
Changing anything in this file changes payload bytes, so bump ``generator_version``
in every set file when you do.
"""

import random

PLACES = (
    "Saltmarsh Quay",
    "the Vellin Hills",
    "Corrow Ford",
    "Ambermouth",
    "the Drewe Basin",
    "Lowtide Market",
    "Harrowgate Pier",
    "the Sunken Weir",
    "Pellam Crossing",
    "Northfold",
)
SURVEYORS = (
    "Surveyor Adda Wren",
    "Clerk Tobin Vale",
    "Archivist Merel Quist",
    "Pilot Joran Teague",
    "Warden Sefa Lund",
    "Cartographer Ivo Brask",
)
THINGS = (
    "tide gauge",
    "signal mast",
    "grain store",
    "rope bridge",
    "salt pan",
    "boathouse",
    "weather vane",
    "ferry ramp",
    "stone cistern",
    "net loft",
)
CONDITIONS = (
    "weathered",
    "freshly tarred",
    "leaning slightly",
    "in good repair",
    "half buried in sand",
    "recently repainted",
    "missing two planks",
    "overgrown with thrift",
)
SEASONS = (
    "early spring",
    "late summer",
    "the autumn gales",
    "the dry season",
    "midwinter",
    "the first thaw",
)
ACTIONS = ("measured", "inspected", "sketched", "logged", "repaired", "surveyed")
CLOSINGS = (
    "No further action was recommended.",
    "A follow-up visit was scheduled.",
    "The entry was countersigned the next morning.",
    "The notes were filed with the harbour office.",
    "Nothing unusual was recorded.",
)

TEMPLATES = (
    "The {thing} at {place} was {condition} when {surveyor} {action} it during {season}.",
    "{surveyor} {action} the {thing} near {place} and counted {num} rivets along its frame.",
    "During {season}, the {thing} at {place} stood {num} paces from the old {thing2}.",
    "According to {surveyor}, the {thing} by {place} had been {condition} for {num} days.",
    "Travellers from {place} reported that the {thing} was {condition} again.",
    "{surveyor} noted that the path from {place} to {place2} took {num} minutes on foot.",
    "In {season}, {surveyor} {action} {num} entries about the {thing} at {place}.",
    "The ledger for {place} lists the {thing} as {condition}, with a note from {surveyor}.",
)


def sentence(rng: random.Random) -> str:
    """One filler sentence. Every slot is drawn on every call, whether the chosen
    template uses it or not, so the random stream never depends on which template won."""
    template = rng.choice(TEMPLATES)
    slots = {
        "place": rng.choice(PLACES),
        "place2": rng.choice(PLACES),
        "surveyor": rng.choice(SURVEYORS),
        "thing": rng.choice(THINGS),
        "thing2": rng.choice(THINGS),
        "condition": rng.choice(CONDITIONS),
        "season": rng.choice(SEASONS),
        "action": rng.choice(ACTIONS),
        "num": rng.randint(2, 999),
    }
    return template.format(**slots)


def paragraph(rng: random.Random) -> str:
    """Four to six sentences and a closing remark."""
    count = rng.randint(4, 6)
    return " ".join([*(sentence(rng) for _ in range(count)), rng.choice(CLOSINGS)])
