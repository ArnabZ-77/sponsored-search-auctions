import random
import time

import pytest

from sponsored_search import AuctionHouse, SearchTerm
from support import MECHANISMS, TERM, enroll

KEY = SearchTerm(TERM)


def large_market(ranking, pricing, bidders: int, slots: int, seed: int = 0) -> AuctionHouse:
    rng = random.Random(seed)
    house = AuctionHouse(ranking, pricing, slots)
    for i in range(bidders):
        enroll(house, f"b{i}", rng.randint(1, 10_000) / 100, rng.randint(0, 5_000) / 100, rng.randint(1, 10))
    return house


@pytest.mark.parametrize("ranking, pricing", MECHANISMS)
def test_two_thousand_bidders_are_auctioned_well_under_a_second(ranking, pricing):
    house = large_market(ranking, pricing, bidders=2_000, slots=10)
    started = time.perf_counter()
    result = house.search(TERM)
    assert time.perf_counter() - started < 1.0
    assert len(result.awards) == 10


@pytest.mark.parametrize("ranking, pricing", MECHANISMS)
def test_awards_are_ordered_by_descending_score_and_priced_within_offers(ranking, pricing):
    house = large_market(ranking, pricing, bidders=500, slots=25)
    ranking_by_score = ranking.rank([bidder.bid_for(KEY) for bidder in house.bidders], house._weights)
    result = house.search(TERM)
    assert [award.bid for award in result.awards] == [ranked.bid for ranked in ranking_by_score[:25]]
    assert all(award.price_per_click <= award.bid.effective_bid for award in result.awards)


@pytest.mark.parametrize("ranking, pricing", MECHANISMS)
def test_a_thousand_searches_with_clicks_never_overrun_any_budget(ranking, pricing):
    rng = random.Random(1)
    house = large_market(ranking, pricing, bidders=50, slots=5, seed=1)
    budgets = {bidder: bidder.bid_for(KEY).remaining_budget for bidder in house.bidders}
    for _ in range(1_000):
        result = house.search(TERM)
        for award in result.awards:
            if rng.random() < 0.3 and award.bid.remaining_budget >= award.price_per_click:
                result.click(award.position)
    assert all(bidder.bid_for(KEY).spent <= budgets[bidder] for bidder in house.bidders)
    assert any(bidder.bid_for(KEY).is_exhausted for bidder in house.bidders)


@pytest.mark.parametrize("ranking, pricing", MECHANISMS)
def test_every_bidder_tied_on_score_is_ranked_in_registration_order(ranking, pricing):
    house = AuctionHouse(ranking, pricing, slots=100)
    for i in range(100):
        enroll(house, f"b{i:03}", "0.50")
    assert [bidder.name for bidder in house.search(TERM).winners] == [f"b{i:03}" for i in range(100)]


@pytest.mark.parametrize("ranking, pricing", MECHANISMS)
def test_bidders_with_no_budget_are_ignored_even_in_a_large_market(ranking, pricing):
    house = large_market(ranking, pricing, bidders=300, slots=300)
    for bidder in house.bidders:
        bidder.bid_for(KEY).update(budget=bidder.bid_for(KEY).spent)
    assert house.search(TERM).awards == ()
