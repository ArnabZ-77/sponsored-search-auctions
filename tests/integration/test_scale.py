import random
import time
from decimal import Decimal

import pytest

from sponsored_search import AuctionHouse, SearchTerm
from support import MECHANISMS, TERM, enroll

KEY = SearchTerm(TERM)


def large_market(ranking, pricing, bidders: int, slots: int, seed: int = 0):
    """Returns the house and the weights the auctioneer assigned, so tests never read its internals."""
    rng = random.Random(seed)
    house = AuctionHouse(ranking, pricing, slots)
    weights = {}
    for i in range(bidders):
        weight = rng.randint(1, 10)
        bidder = enroll(house, f"b{i}", rng.randint(1, 10_000) / 100, rng.randint(0, 5_000) / 100, weight)
        weights[bidder] = Decimal(weight)
    return house, weights


@pytest.mark.parametrize("ranking, pricing", MECHANISMS)
def test_two_thousand_bidders_are_auctioned_well_under_a_second(ranking, pricing):
    house, _ = large_market(ranking, pricing, bidders=2_000, slots=10)
    started = time.perf_counter()
    result = house.search(TERM)
    assert time.perf_counter() - started < 1.0
    assert len(result.awards) == 10


@pytest.mark.parametrize("ranking, pricing", MECHANISMS)
def test_awards_are_ordered_by_descending_score_and_beat_every_loser(ranking, pricing):
    house, weights = large_market(ranking, pricing, bidders=500, slots=25)
    result = house.search(TERM)

    def score_of(bidder):
        return bidder.bid_for(KEY).effective_bid * ranking.weight_of(bidder.bid_for(KEY), weights)

    awarded = [score_of(award.bidder) for award in result.awards]
    assert awarded == sorted(awarded, reverse=True)
    losers = [bidder for bidder in house.bidders if bidder not in result.winners]
    assert all(score_of(loser) <= awarded[-1] for loser in losers)
    assert all(award.price_per_click <= award.bid.effective_bid for award in result.awards)


@pytest.mark.parametrize("ranking, pricing", MECHANISMS)
def test_a_thousand_searches_with_clicks_never_overrun_any_budget(ranking, pricing):
    rng = random.Random(1)
    house, _ = large_market(ranking, pricing, bidders=50, slots=5, seed=1)
    budgets = {bidder: bidder.bid_for(KEY).remaining_budget for bidder in house.bidders}
    for _ in range(1_000):
        result = house.search(TERM)
        for award in result.awards:
            if rng.random() < 0.3 and award.bid.remaining_budget >= award.price_per_click:
                result.click(award.position)
    assert all(bidder.bid_for(KEY).spent <= budgets[bidder] for bidder in house.bidders)
    assert any(bidder.bid_for(KEY).is_exhausted for bidder in house.bidders)


@pytest.mark.parametrize("ranking, pricing", MECHANISMS)
def test_every_bidder_tied_on_score_is_ranked_in_arrival_order(ranking, pricing):
    house = AuctionHouse(ranking, pricing, slots=100)
    for i in range(100):
        enroll(house, f"b{i:03}", "0.50")
    assert [bidder.name for bidder in house.search(TERM).winners] == [f"b{i:03}" for i in range(100)]


@pytest.mark.parametrize("ranking, pricing", MECHANISMS)
def test_bidders_with_no_budget_are_ignored_even_in_a_large_market(ranking, pricing):
    house, _ = large_market(ranking, pricing, bidders=300, slots=300)
    for bidder in house.bidders:
        bidder.bid_for(KEY).update(budget=bidder.bid_for(KEY).spent)
    assert house.search(TERM).awards == ()
