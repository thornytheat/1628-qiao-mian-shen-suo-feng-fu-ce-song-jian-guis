from copy import deepcopy

import pytest

from jointfolio.joint_register.service import known_labels, sample, stage
from jointfolio.thermal_alignment.service import encode, learn_bank
from jointfolio.joint_sen_fit.service import fit
from jointfolio.bridge_residuals.service import split
from jointfolio.engine import ROOT, plan
from jointfolio.settings import DEFAULT_DAY, FIELD_BOUNDS, GROUPS


@pytest.fixture(scope="session")
def original():
    return sample(ROOT)


@pytest.fixture
def packet(original):
    return deepcopy(original)


@pytest.fixture
def observation():
    return {
        "case_id": "QA-HD",
        "group": GROUPS[0],
        "day": 22,
        "arrived": 22,
        "revision": 1,
        "clock": 32,
        "measurements": {
            key: (0 if (lo, hi) == (0, 1) else (lo + hi) / 2)
            for key, (lo, hi) in FIELD_BOUNDS.items()
        },
    }


@pytest.fixture(scope="session")
def learning(original):
    book = stage(original, DEFAULT_DAY)
    boundary = split(DEFAULT_DAY)
    historical = stage(original, boundary.train_before - 1)
    bank = learn_bank(historical.observations, boundary.train_before)
    signals = [encode(row, bank) for row in book.observations]
    history = [encode(row, bank) for row in historical.observations]
    model = fit(history, known_labels(historical, boundary.train_before - 1))
    return book, boundary, bank, signals, history, model


@pytest.fixture(scope="session")
def report(original):
    return plan(original)
