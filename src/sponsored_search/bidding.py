from __future__ import annotations

from dataclasses import dataclass

from .money import ZERO, Money


class BudgetExhausted(Exception):
    pass


@dataclass(frozen=True)
class SearchTerm:
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", " ".join(self.text.casefold().split()))
        if not self.text:
            raise ValueError("search term must not be blank")


class Bid:
    def __init__(self, bidder: Bidder, term: SearchTerm, max_price: Money, budget: Money) -> None:
        self.bidder = bidder
        self.term = term
        self._spent = ZERO
        self.update(max_price=max_price, budget=budget)

    def update(self, *, max_price: Money | None = None, budget: Money | None = None) -> None:
        if max_price is not None:
            if max_price <= ZERO:
                raise ValueError("max price must be positive")
            self._max_price = max_price
        if budget is not None:
            if budget < ZERO:
                raise ValueError("budget must not be negative")
            self._budget = budget

    @property
    def spent(self) -> Money:
        return self._spent

    @property
    def remaining_budget(self) -> Money:
        return max(ZERO, self._budget - self._spent)

    @property
    def effective_bid(self) -> Money:
        """The most this bid can actually pay for one click: min(max price, remaining budget)."""
        return min(self._max_price, self.remaining_budget)

    @property
    def is_exhausted(self) -> bool:
        return self.remaining_budget == ZERO

    def charge(self, price: Money) -> None:
        if price > self.remaining_budget:
            raise BudgetExhausted(f"{self.bidder} cannot pay {price} per click for '{self.term.text}'")
        self._spent += price

    def __repr__(self) -> str:
        return f"Bid({self.bidder}, '{self.term.text}', offers {self.effective_bid})"


class Bidder:
    def __init__(self, name: str) -> None:
        self.name = name
        self._bids: dict[SearchTerm, Bid] = {}

    def place_bid(self, term: str, max_price: Money, budget: Money) -> Bid:
        key = SearchTerm(term)
        if key in self._bids:
            self._bids[key].update(max_price=max_price, budget=budget)
        else:
            self._bids[key] = Bid(self, key, max_price, budget)
        return self._bids[key]

    def bid_for(self, term: SearchTerm) -> Bid | None:
        return self._bids.get(term)

    def __repr__(self) -> str:
        return self.name
