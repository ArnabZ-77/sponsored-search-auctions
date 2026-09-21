from decimal import Decimal

import pytest

from sponsored_search import (
    AuctionHouse,
    Bidder,
    BudgetExhausted,
    GeneralizedSecondPrice,
    RankByBid,
    RankByScore,
    SearchTerm,
)
from support import TERM, enroll, money, prices


def house(ranking=None, slots=2, reserve="0") -> AuctionHouse:
    return AuctionHouse(ranking or RankByBid(), GeneralizedSecondPrice(), slots, money(reserve))


def test_bids_placed_before_registering_still_enter_the_auction():
    auction, bidder = house(), Bidder("late")
    bidder.place_bid(TERM, money("0.50"), money(10))
    auction.register(bidder)
    assert auction.search(TERM).winners == (bidder,)


def test_a_bidder_can_compete_in_two_auction_systems_under_different_weights():
    strict, generous = house(RankByScore(), slots=1), house(RankByScore(), slots=1)
    shared, rival_a, rival_b = Bidder("shared"), Bidder("a"), Bidder("b")
    strict.register(shared, Decimal(3))
    strict.register(rival_a)
    generous.register(shared)
    generous.register(rival_b, Decimal(3))
    for bidder in (shared, rival_a, rival_b):
        bidder.place_bid(TERM, money("0.20" if bidder is shared else "0.40"), money(10))
    assert strict.search(TERM).winners == (shared,)
    assert generous.search(TERM).winners == (rival_b,)


def test_a_click_in_one_auction_system_depletes_the_bid_everywhere():
    first, second = house(slots=1), house(slots=1)
    bidder = Bidder("shared")
    first.register(bidder)
    second.register(bidder)
    bid = bidder.place_bid(TERM, money("0.50"), money("0.40"))
    enroll(first, "rival", "0.40")
    assert first.search(TERM).click(1) == money("0.40")
    assert bid.is_exhausted
    assert second.search(TERM).awards == ()


def test_registering_the_same_bidder_repeatedly_indexes_its_bids_once():
    auction, bidder = house(slots=3), Bidder("dup")
    bidder.place_bid(TERM, money("0.50"), money(10))
    for _ in range(3):
        auction.register(bidder)
    assert len(auction.search(TERM).awards) == 1


def test_ties_go_to_whichever_bid_was_registered_first():
    """Arrival order is the bid's, not the bidder's: a bidder is only in an auction once it has bid."""
    auction = house(slots=2)
    early, late = Bidder("early"), Bidder("late")
    auction.register(late)
    auction.register(early)
    early.place_bid(TERM, money("0.50"), money(10))
    late.place_bid(TERM, money("0.50"), money(10))
    assert [bidder.name for bidder in auction.search(TERM).winners] == ["early", "late"]


@pytest.mark.parametrize("max_price, participates", [("0.50", True), ("0.05", True), ("0.04", False)])
def test_the_reserve_price_is_inclusive(max_price, participates):
    auction = house(reserve="0.05", slots=3)
    enroll(auction, "other", "0.50")
    candidate = enroll(auction, "candidate", max_price, budget=10)
    assert (candidate in auction.search(TERM).winners) is participates


def test_an_auction_where_nobody_meets_the_reserve_awards_nothing():
    auction = house(reserve="0.05", slots=2)
    enroll(auction, "cheap", "0.03")
    assert auction.search(TERM).awards == ()


def test_the_lowest_winner_pays_the_reserve_rather_than_zero():
    auction = house(reserve="0.05", slots=3)
    enroll(auction, "top", "0.50")
    enroll(auction, "bottom", "0.20")
    assert prices(auction.search(TERM)) == [("top", "0.20"), ("bottom", "0.05")]


def test_a_result_cannot_overrun_a_budget_lowered_after_the_auction_ran():
    auction = house(slots=1)
    bid = enroll(auction, "A", "0.50").bid_for(SearchTerm(TERM))
    enroll(auction, "B", "0.30")
    result = auction.search(TERM)
    bid.update(budget=money("0.10"))
    with pytest.raises(BudgetExhausted):
        result.click(1)
    assert bid.spent == money(0)
