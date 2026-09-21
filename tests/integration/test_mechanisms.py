import pytest

from sponsored_search import (
    ZERO,
    AuctionHouse,
    GeneralizedFirstPrice,
    GeneralizedSecondPrice,
    RankByBid,
    RankByScore,
)
from support import MECHANISMS, TERM, enroll, money, prices


def three_bidders_two_slots(ranking, pricing, **house_options) -> AuctionHouse:
    house = AuctionHouse(ranking, pricing, slots=2, **house_options)
    enroll(house, "A", "0.50", weight=1)
    enroll(house, "B", "0.30", weight=2)
    enroll(house, "C", "0.20", weight=1)
    return house


@pytest.mark.parametrize(
    "ranking, pricing, expected",
    [
        (RankByBid(), GeneralizedFirstPrice(), [("A", "0.50"), ("B", "0.30")]),
        (RankByBid(), GeneralizedSecondPrice(), [("A", "0.30"), ("B", "0.20")]),
        (RankByScore(), GeneralizedFirstPrice(), [("B", "0.30"), ("A", "0.50")]),
        (RankByScore(), GeneralizedSecondPrice(), [("B", "0.25"), ("A", "0.20")]),
    ],
    ids=["rank-by-bid/GFP", "rank-by-bid/GSP", "rank-by-score/GFP", "rank-by-score/GSP"],
)
def test_each_mechanism_allocates_and_prices_the_slots(ranking, pricing, expected):
    assert prices(three_bidders_two_slots(ranking, pricing).search(TERM)) == expected


@pytest.mark.parametrize("ranking, pricing", MECHANISMS)
class TestEveryMechanism:
    def test_nobody_pays_more_than_they_offered(self, ranking, pricing):
        for award in three_bidders_two_slots(ranking, pricing).search(TERM).awards:
            assert award.price_per_click <= award.bid.effective_bid

    def test_awards_never_exceed_the_number_of_slots(self, ranking, pricing):
        assert len(three_bidders_two_slots(ranking, pricing).search(TERM).awards) == 2

    def test_a_bidder_wins_at_most_one_slot(self, ranking, pricing):
        house = AuctionHouse(ranking, pricing, slots=3)
        keen = enroll(house, "keen", "0.90")
        keen.place_bid(TERM, money("0.95"), money(100))
        other = enroll(house, "other", "0.10")
        assert house.search(TERM).winners == (keen, other)

    def test_registering_a_bidder_twice_cannot_earn_it_two_slots(self, ranking, pricing):
        house = AuctionHouse(ranking, pricing, slots=3)
        keen = enroll(house, "keen", "0.90")
        house.register(keen)
        other = enroll(house, "other", "0.10")
        assert house.search(TERM).winners == (keen, other)

    def test_clicking_an_empty_or_invalid_slot_is_rejected_and_charges_nobody(self, ranking, pricing):
        house = three_bidders_two_slots(ranking, pricing)
        result = house.search(TERM)
        for position in (0, 3, -1):
            with pytest.raises(ValueError):
                result.click(position)
        assert all(bidder.bid_for(result.term).spent == ZERO for bidder in house.bidders)

    def test_losers_and_unclicked_winners_pay_nothing(self, ranking, pricing):
        house = three_bidders_two_slots(ranking, pricing)
        result = house.search(TERM)
        result.click(1)
        assert result.awards[1].bid.spent == ZERO
        losers = [bidder for bidder in house.bidders if bidder not in result.winners]
        assert all(loser.bid_for(result.term).spent == ZERO for loser in losers)

    def test_a_click_charges_exactly_the_slot_price(self, ranking, pricing):
        result = three_bidders_two_slots(ranking, pricing).search(TERM)
        for award in result.awards:
            assert result.click(award.position) == award.price_per_click
            assert award.bid.spent == award.price_per_click

    def test_a_search_nobody_bid_on_yields_no_awards(self, ranking, pricing):
        assert three_bidders_two_slots(ranking, pricing).search("flowers").awards == ()

    def test_fewer_bidders_than_slots_leaves_slots_empty(self, ranking, pricing):
        house = AuctionHouse(ranking, pricing, slots=5)
        enroll(house, "only", "0.50")
        assert [award.position for award in house.search(TERM).awards] == [1]

    def test_search_terms_match_regardless_of_case_and_spacing(self, ranking, pricing):
        house = three_bidders_two_slots(ranking, pricing)
        assert prices(house.search("  Tyre   SHOP software ")) == prices(house.search(TERM))

    def test_ties_go_to_the_earlier_registered_bidder(self, ranking, pricing):
        house = AuctionHouse(ranking, pricing, slots=1)
        enroll(house, "early", "0.50")
        enroll(house, "late", "0.50")
        assert house.search(TERM).winners[0].name == "early"


def test_last_slot_is_priced_off_the_first_bidder_who_won_nothing():
    result = three_bidders_two_slots(RankByBid(), GeneralizedSecondPrice()).search(TERM)
    assert prices(result) == [("A", "0.30"), ("B", "0.20")]
    assert "C" not in [bidder.name for bidder in result.winners]


def test_lone_bidder_pays_nothing_under_second_price_without_a_reserve():
    house = AuctionHouse(RankByBid(), GeneralizedSecondPrice(), slots=1)
    enroll(house, "only", "0.50")
    assert prices(house.search(TERM)) == [("only", "0.00")]


def test_reserve_price_is_the_floor_for_the_lowest_ranked_winner():
    house = AuctionHouse(RankByBid(), GeneralizedSecondPrice(), slots=2, reserve_price=money("0.05"))
    enroll(house, "A", "0.50")
    enroll(house, "B", "0.02")
    assert prices(house.search(TERM)) == [("A", "0.05")]


def test_edelman_ostrovsky_schwarz_two_slot_example():
    """AER 2007, section I: bids 10, 4, 2 for two slots; slot 1 pays 4, slot 2 pays 2."""
    house = AuctionHouse(RankByBid(), GeneralizedSecondPrice(), slots=2)
    for name, bid in [("x", 10), ("y", 4), ("z", 2)]:
        enroll(house, name, bid)
    assert prices(house.search(TERM)) == [("x", "4.00"), ("y", "2.00")]
