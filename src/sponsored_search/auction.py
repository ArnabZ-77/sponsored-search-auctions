from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from .bidding import Bid, Bidder, SearchTerm
from .money import CENT, ZERO, Money
from .pricing import PricingStrategy
from .ranking import UNIT, RankedBid, RankingStrategy


@dataclass(frozen=True)
class SlotAward:
    position: int
    bid: Bid
    price_per_click: Money

    @property
    def bidder(self) -> Bidder:
        return self.bid.bidder


@dataclass(frozen=True)
class AuctionResult:
    term: SearchTerm
    awards: tuple[SlotAward, ...]

    @property
    def winners(self) -> tuple[Bidder, ...]:
        return tuple(award.bidder for award in self.awards)

    def click(self, position: int) -> Money:
        if not 1 <= position <= len(self.awards):
            raise ValueError(f"no sponsored result in slot {position}")
        award = self.awards[position - 1]
        award.bid.charge(award.price_per_click)
        return award.price_per_click


class AuctionHouse:
    def __init__(
        self, ranking: RankingStrategy, pricing: PricingStrategy, slots: int, reserve_price: Money = ZERO
    ) -> None:
        if slots < 1:
            raise ValueError("an auction needs at least one slot")
        if reserve_price < ZERO:
            raise ValueError("reserve price must not be negative")
        self._ranking, self._pricing, self._slots, self._reserve = ranking, pricing, slots, reserve_price
        self._floor = max(reserve_price, CENT)
        self._weights: dict[Bidder, Decimal] = {}
        self._bids: dict[SearchTerm, list[Bid]] = {}

    @property
    def bidders(self) -> tuple[Bidder, ...]:
        return tuple(self._weights)

    def register(self, bidder: Bidder, weight: Decimal = UNIT) -> Bidder:
        joining = bidder not in self._weights
        self.set_weight(bidder, weight)
        if joining:
            bidder.register_with(self._enlist)
        return bidder

    def set_weight(self, bidder: Bidder, weight: Decimal) -> None:
        if weight <= 0:
            raise ValueError("weight must be positive")
        self._weights[bidder] = weight

    def search(self, term: str) -> AuctionResult:
        """Only bids registered for this term are considered, so cost tracks competition, not catalogue size."""
        key = SearchTerm(term)
        ranking = self._ranking.rank(self._bids.get(key, ()), self._weights, self._floor)
        return AuctionResult(
            key,
            tuple(
                SlotAward(position + 1, ranked.bid, self._price(ranking, position))
                for position, ranked in enumerate(ranking[: self._slots])
            ),
        )

    def _enlist(self, bid: Bid) -> None:
        self._bids.setdefault(bid.term, []).append(bid)

    def _price(self, ranking: Sequence[RankedBid], position: int) -> Money:
        """No bidder ever pays more than it offered, nor less than the reserve."""
        return min(ranking[position].offer, max(self._reserve, self._pricing.price(ranking, position)))
