import random

import pytest

from sponsored_search import (
    AuctionHouse,
    AuctionResult,
    Bidder,
    BudgetExhausted,
    GeneralizedFirstPrice,
    GeneralizedSecondPrice,
    RankByBid,
    RankByScore,
    SearchTerm,
    SlotAward,
)
from support import MECHANISMS, TERM, enroll, money, prices

SEEDS = range(6)
KEY = SearchTerm(TERM)


def random_specs(rng: random.Random):
    weights = ["0.5", "1", "1.5", "2", "3"]
    return [
        (f"b{i}", rng.randint(1, 500) / 100, rng.randint(0, 300) / 100, rng.choice(weights))
        for i in range(rng.randint(1, 8))
    ]


def market(ranking, pricing, slots, specs, weighted=True) -> AuctionHouse:
    house = AuctionHouse(ranking, pricing, slots)
    for name, price, budget, weight in specs:
        enroll(house, name, price, budget, weight if weighted else 1)
    return house


def click_a_few_times(result: AuctionResult, award: SlotAward, rng: random.Random) -> None:
    for _ in range(rng.randint(0, 3)):
        try:
            result.click(award.position)
        except BudgetExhausted:
            assert award.bid.remaining_budget < award.price_per_click


def position_of(result: AuctionResult, bidder: Bidder) -> int:
    return result.winners.index(bidder) + 1 if bidder in result.winners else len(result.awards) + 1


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("ranking, pricing", MECHANISMS)
def test_budgets_are_never_overrun_and_nobody_pays_more_than_offered(ranking, pricing, seed):
    rng = random.Random(seed)
    slots = rng.randint(1, 4)
    specs = random_specs(rng)
    house = market(ranking, pricing, slots, specs)
    budgets = {name: money(budget) for name, _, budget, _ in specs}
    for _ in range(40):
        result = house.search(TERM)
        assert len(result.awards) <= slots
        assert len(set(result.winners)) == len(result.winners)
        assert all(award.price_per_click <= award.bid.effective_bid for award in result.awards)
        for award in result.awards:
            click_a_few_times(result, award, rng)
        assert all(bidder.bid_for(KEY).spent <= budgets[bidder.name] for bidder in house.bidders)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("pricing", [GeneralizedFirstPrice(), GeneralizedSecondPrice()], ids=["GFP", "GSP"])
def test_rank_by_bid_and_rank_by_score_agree_when_all_weights_are_equal(pricing, seed):
    specs = random_specs(random.Random(seed))
    by_bid = market(RankByBid(), pricing, 3, specs, weighted=False)
    by_score = market(RankByScore(), pricing, 3, specs, weighted=False)
    assert prices(by_bid.search(TERM)) == prices(by_score.search(TERM))


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("ranking", [RankByBid(), RankByScore()], ids=["rank-by-bid", "rank-by-score"])
def test_second_price_never_charges_more_than_first_price_for_the_same_slot(ranking, seed):
    specs = random_specs(random.Random(seed))
    first = market(ranking, GeneralizedFirstPrice(), 3, specs).search(TERM)
    second = market(ranking, GeneralizedSecondPrice(), 3, specs).search(TERM)
    assert [w.name for w in first.winners] == [w.name for w in second.winners]
    assert all(s.price_per_click <= f.price_per_click for f, s in zip(first.awards, second.awards, strict=True))


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("ranking, pricing", MECHANISMS)
def test_raising_your_bid_never_costs_you_your_position(ranking, pricing, seed):
    rng = random.Random(seed)
    specs = [(name, price, 100, weight) for name, price, _, weight in random_specs(rng)]
    house = market(ranking, pricing, 3, specs)
    name, price, _, _ = rng.choice(specs)
    bidder = next(bidder for bidder in house.bidders if bidder.name == name)
    before = position_of(house.search(TERM), bidder)
    bidder.place_bid(TERM, money(price + 1), money(100))
    assert position_of(house.search(TERM), bidder) <= before
