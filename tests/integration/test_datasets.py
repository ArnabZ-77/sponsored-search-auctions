import json
from decimal import Decimal
from pathlib import Path

import pytest

from sponsored_search import (
    AuctionHouse,
    Bidder,
    GeneralizedFirstPrice,
    GeneralizedSecondPrice,
    RankByBid,
    RankByScore,
)
from support import TERM, money, prices

DATASETS = sorted((Path(__file__).parent.parent / "datasets").glob("*.json"))
RANKINGS = {"bid": RankByBid, "score": RankByScore}
PRICINGS = {"first": GeneralizedFirstPrice, "second": GeneralizedSecondPrice}


def load(path: Path) -> tuple[AuctionHouse, list[list[str]]]:
    scenario = json.loads(path.read_text())
    house = AuctionHouse(
        RANKINGS[scenario["ranking"]](),
        PRICINGS[scenario["pricing"]](),
        scenario["slots"],
        money(scenario.get("reserve", 0)),
    )
    for name, max_price, budget, weight in scenario["bidders"]:
        house.register(Bidder(name), Decimal(weight)).place_bid(TERM, money(max_price), money(budget))
    return house, scenario["expected"]


@pytest.mark.parametrize("path", DATASETS, ids=[path.stem for path in DATASETS])
def test_scenario_from_dataset(path: Path):
    house, expected = load(path)
    assert prices(house.search(TERM)) == [tuple(award) for award in expected]
