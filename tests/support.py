from decimal import Decimal

import pytest

from sponsored_search import (
    AuctionHouse,
    AuctionResult,
    Bidder,
    GeneralizedFirstPrice,
    GeneralizedSecondPrice,
    Money,
    RankByBid,
    RankByScore,
)

TERM = "tyre shop software"

MECHANISMS = [
    pytest.param(RankByBid(), GeneralizedFirstPrice(), id="rank-by-bid/GFP"),
    pytest.param(RankByBid(), GeneralizedSecondPrice(), id="rank-by-bid/GSP"),
    pytest.param(RankByScore(), GeneralizedFirstPrice(), id="rank-by-score/GFP"),
    pytest.param(RankByScore(), GeneralizedSecondPrice(), id="rank-by-score/GSP"),
]


def money(value) -> Money:
    return Money.of(value)


def enroll(house: AuctionHouse, name: str, max_price, budget=100, weight=1, term=TERM) -> Bidder:
    bidder = house.register(Bidder(name), Decimal(str(weight)))
    bidder.place_bid(term, money(max_price), money(budget))
    return bidder


def prices(result: AuctionResult) -> list[tuple[str, str]]:
    return [(award.bidder.name, str(award.price_per_click)) for award in result.awards]
