from decimal import Decimal

from sponsored_search import AuctionHouse, GeneralizedSecondPrice, RankByBid, RankByScore
from support import enroll, money, prices


def test_boosting_a_bid_before_valentines_day_takes_the_top_slot():
    house = AuctionHouse(RankByBid(), GeneralizedSecondPrice(), slots=2)
    enroll(house, "A", "0.50", term="flowers")
    florist = enroll(house, "B", "0.30", term="flowers")
    assert prices(house.search("flowers")) == [("A", "0.30"), ("B", "0.00")]
    florist.place_bid("flowers", money("0.80"), money(100))
    assert prices(house.search("flowers")) == [("B", "0.50"), ("A", "0.00")]


def test_lowering_a_bid_gives_up_the_slot():
    house = AuctionHouse(RankByBid(), GeneralizedSecondPrice(), slots=1)
    leader = enroll(house, "A", "0.50")
    enroll(house, "B", "0.30")
    leader.place_bid("tyre shop software", money("0.10"), money(100))
    assert prices(house.search("tyre shop software")) == [("B", "0.10")]


def test_auctioneer_can_reweight_bidders_between_auctions():
    house = AuctionHouse(RankByScore(), GeneralizedSecondPrice(), slots=1)
    a = enroll(house, "A", "0.50")
    enroll(house, "B", "0.30")
    assert prices(house.search("tyre shop software")) == [("A", "0.30")]
    house.set_weight(a, Decimal("0.5"))
    assert prices(house.search("tyre shop software")) == [("B", "0.25")]


def test_weights_never_influence_rank_by_bid():
    house = AuctionHouse(RankByBid(), GeneralizedSecondPrice(), slots=1)
    enroll(house, "A", "0.50", weight="0.1")
    enroll(house, "B", "0.30", weight="10")
    assert prices(house.search("tyre shop software")) == [("A", "0.30")]


def test_bidders_can_enter_new_keywords_at_any_time():
    house = AuctionHouse(RankByBid(), GeneralizedSecondPrice(), slots=1)
    bidder = enroll(house, "A", "0.50")
    assert house.search("flowers").awards == ()
    bidder.place_bid("flowers", money("0.20"), money(10))
    assert prices(house.search("flowers")) == [("A", "0.00")]


def test_every_search_is_a_fresh_auction_on_current_state():
    house = AuctionHouse(RankByBid(), GeneralizedSecondPrice(), slots=1)
    enroll(house, "A", "0.50")
    enroll(house, "B", "0.30", budget="0.30")
    first = house.search("tyre shop software")
    assert prices(first) == [("A", "0.30")]
    house.search("tyre shop software").click(1)
    assert prices(house.search("tyre shop software")) == [("A", "0.30")]
    first.awards[0].bid.bidder.place_bid("tyre shop software", money("0.50"), money("0.00"))
    assert prices(house.search("tyre shop software")) == [("B", "0.00")]
