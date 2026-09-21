from decimal import Decimal

from sponsored_search import ZERO, Bidder, GeneralizedFirstPrice, GeneralizedSecondPrice, RankByScore
from support import TERM, money


def ranking_of(*specs):
    weights, bids = {}, []
    for name, price, weight in specs:
        bids.append(Bidder(name).place_bid(TERM, money(price), money(100)))
        weights[bids[-1].bidder] = Decimal(weight)
    return RankByScore().rank(bids, weights)


def test_first_price_charges_each_position_its_own_bid():
    ranking = ranking_of(("a", "0.50", 1), ("b", "0.30", 2))
    assert [GeneralizedFirstPrice().price(ranking, i) for i in range(2)] == [money("0.30"), money("0.50")]


def test_second_price_charges_the_next_score_divided_by_own_weight():
    ranking = ranking_of(("a", "0.50", 1), ("b", "0.30", 2), ("c", "0.20", 1))
    assert [GeneralizedSecondPrice().price(ranking, i) for i in range(3)] == [money("0.25"), money("0.20"), ZERO]


def test_second_price_reduces_to_the_next_bid_under_unit_weights():
    ranking = ranking_of(("a", "0.50", 1), ("b", "0.30", 1))
    assert GeneralizedSecondPrice().price(ranking, 0) == money("0.30")


def test_second_price_rounds_to_the_cent():
    ranking = ranking_of(("a", "1.00", 3), ("b", "1.00", 1))
    assert GeneralizedSecondPrice().price(ranking, 0) == money("0.33")


def test_last_ranked_participant_pays_nothing_under_second_price():
    ranking = ranking_of(("only", "0.50", 1))
    assert GeneralizedSecondPrice().price(ranking, 0) == ZERO
