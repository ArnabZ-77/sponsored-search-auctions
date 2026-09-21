import pytest

from sponsored_search import (
    AuctionHouse,
    BudgetExhausted,
    GeneralizedFirstPrice,
    GeneralizedSecondPrice,
    RankByBid,
    SearchTerm,
)
from support import MECHANISMS, TERM, enroll, money, prices


@pytest.mark.parametrize("ranking, pricing", MECHANISMS)
class TestBudgetsUnderEveryMechanism:
    def test_spend_never_exceeds_the_budget_however_often_users_click(self, ranking, pricing):
        house = AuctionHouse(ranking, pricing, slots=1)
        bid = enroll(house, "A", "0.40", budget="1.00").bid_for(SearchTerm(TERM))
        enroll(house, "B", "0.30")
        result = house.search(TERM)
        with pytest.raises(BudgetExhausted):
            for _ in range(10):
                result.click(1)
        assert bid.spent <= money("1.00")
        assert bid.spent + result.awards[0].price_per_click > money("1.00")

    def test_exhausted_bidders_sit_out_the_auction(self, ranking, pricing):
        house = AuctionHouse(ranking, pricing, slots=2)
        enroll(house, "broke", "0.90", budget="0.50").bid_for(SearchTerm(TERM)).charge(money("0.50"))
        enroll(house, "solvent", "0.10")
        assert house.search(TERM).winners[0].name == "solvent"
        assert len(house.search(TERM).awards) == 1

    def test_a_low_budget_bidder_competes_with_what_it_can_still_pay(self, ranking, pricing):
        house = AuctionHouse(ranking, pricing, slots=2)
        enroll(house, "rich", "0.30")
        enroll(house, "poor", "0.90", budget="0.10")
        result = house.search(TERM)
        assert [bidder.name for bidder in result.winners] == ["rich", "poor"]
        assert result.awards[1].price_per_click <= money("0.10")

    def test_topping_up_the_budget_restores_participation(self, ranking, pricing):
        house = AuctionHouse(ranking, pricing, slots=1)
        bidder = enroll(house, "A", "0.50", budget="0.00")
        assert house.search(TERM).awards == ()
        bidder.place_bid(TERM, money("0.50"), money("5.00"))
        assert house.search(TERM).winners == (bidder,)


def test_second_price_runner_up_prices_the_slot_above_by_what_it_could_actually_pay():
    house = AuctionHouse(RankByBid(), GeneralizedSecondPrice(), slots=1)
    enroll(house, "A", "0.50")
    enroll(house, "C", "0.20", budget="0.05")
    assert prices(house.search(TERM)) == [("A", "0.05")]


def test_first_price_charges_a_capped_bidder_its_remaining_budget_not_its_max_price():
    house = AuctionHouse(RankByBid(), GeneralizedFirstPrice(), slots=1)
    enroll(house, "A", "0.90", budget="0.25")
    assert prices(house.search(TERM)) == [("A", "0.25")]


def test_budget_drained_mid_result_refuses_further_clicks_and_caps_the_next_auction():
    house = AuctionHouse(RankByBid(), GeneralizedFirstPrice(), slots=1)
    bid = enroll(house, "A", "0.40", budget="1.00").bid_for(SearchTerm(TERM))
    result = house.search(TERM)
    result.click(1)
    result.click(1)
    with pytest.raises(BudgetExhausted):
        result.click(1)
    assert bid.spent == money("0.80")
    assert prices(house.search(TERM)) == [("A", "0.20")]
