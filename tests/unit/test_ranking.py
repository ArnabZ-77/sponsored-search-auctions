from decimal import Decimal

import pytest

from sponsored_search import Bidder, RankByBid, RankByScore
from support import TERM, money


def bids(*specs):
    return [Bidder(name).place_bid(TERM, money(price), money(budget)) for name, price, budget in specs]


def names(ranking):
    return [ranked.bid.bidder.name for ranked in ranking]


def test_rank_by_bid_orders_by_bid_and_ignores_weights():
    low, high = bids(("low", "0.20", 10), ("high", "0.50", 10))
    ranking = RankByBid().rank([low, high], {low.bidder: Decimal(10)})
    assert names(ranking) == ["high", "low"]
    assert [ranked.weight for ranked in ranking] == [Decimal(1), Decimal(1)]


def test_rank_by_score_orders_by_weight_times_bid():
    a, b = bids(("a", "0.50", 10), ("b", "0.30", 10))
    ranking = RankByScore().rank([a, b], {b.bidder: Decimal(2)})
    assert names(ranking) == ["b", "a"]
    assert [ranked.score for ranked in ranking] == [money("0.60"), money("0.50")]


def test_rank_by_score_defaults_missing_weights_to_one():
    (a,) = bids(("a", "0.50", 10))
    assert RankByScore().rank([a], {})[0].score == money("0.50")


@pytest.mark.parametrize("strategy", [RankByBid(), RankByScore()])
def test_ties_keep_registration_order(strategy):
    first, second, third = bids(("first", "0.50", 10), ("second", "0.50", 10), ("third", "0.50", 10))
    assert names(strategy.rank([first, second, third], {})) == ["first", "second", "third"]


def test_scores_use_budget_capped_effective_bids():
    rich, poor = bids(("rich", "0.30", 10), ("poor", "0.90", "0.10"))
    assert names(RankByBid().rank([rich, poor], {})) == ["rich", "poor"]
