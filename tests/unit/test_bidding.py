import pytest

from sponsored_search import ZERO, Bidder, BudgetExhausted, SearchTerm
from support import TERM, money


@pytest.mark.parametrize(
    "raw, normalised",
    [("Tyre Shop", "tyre shop"), ("  tyre   shop  ", "tyre shop"), ("TYRE", "tyre")],
)
def test_search_terms_normalise_case_and_whitespace(raw, normalised):
    assert SearchTerm(raw) == SearchTerm(normalised)
    assert SearchTerm(raw).text == normalised


def test_blank_search_term_is_rejected():
    with pytest.raises(ValueError):
        SearchTerm("   ")


@pytest.fixture
def bid():
    return Bidder("wheelops").place_bid(TERM, money("0.50"), money(1))


@pytest.mark.parametrize("max_price, budget", [("0", "1"), ("-0.10", "1"), ("0.50", "-1")])
def test_non_positive_prices_and_negative_budgets_are_rejected(max_price, budget):
    with pytest.raises(ValueError):
        Bidder("x").place_bid(TERM, money(max_price), money(budget))


def test_effective_bid_is_the_max_price_capped_by_remaining_budget(bid):
    assert bid.effective_bid == money("0.50")
    bid.update(budget=money("0.20"))
    assert bid.effective_bid == money("0.20")


def test_charging_moves_money_from_budget_to_spent(bid):
    bid.charge(money("0.40"))
    assert (bid.spent, bid.remaining_budget) == (money("0.40"), money("0.60"))


def test_charge_beyond_remaining_budget_is_refused_and_leaves_spend_unchanged(bid):
    bid.charge(money("0.90"))
    with pytest.raises(BudgetExhausted):
        bid.charge(money("0.20"))
    assert bid.spent == money("0.90")


def test_bid_is_exhausted_once_its_budget_is_spent(bid):
    bid.charge(money(1))
    assert bid.is_exhausted
    assert bid.effective_bid == ZERO


def test_lowering_budget_below_spend_exhausts_the_bid_without_refund(bid):
    bid.charge(money("0.50"))
    bid.update(budget=money("0.30"))
    assert bid.is_exhausted
    assert bid.spent == money("0.50")


def test_bidder_keeps_one_bid_per_term_and_updating_it_preserves_spend():
    bidder = Bidder("wheelops")
    original = bidder.place_bid("Tyre Shop", money("0.50"), money(1))
    original.charge(money("0.10"))
    updated = bidder.place_bid("tyre  shop", money("0.80"), money(2))
    assert updated is original
    assert (updated.effective_bid, updated.spent) == (money("0.80"), money("0.10"))


def test_bidder_has_no_bid_for_an_unknown_term():
    assert Bidder("x").bid_for(SearchTerm("flowers")) is None
