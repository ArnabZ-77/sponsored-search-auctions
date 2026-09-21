from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from .bidding import Bid, Bidder, SearchTerm
from .money import ZERO, Money
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
        self,
        ranking: RankingStrategy,
        pricing: PricingStrategy,
        slots: int,
        reserve_price: Money = ZERO,
    ) -> None:
        if slots < 1:
            raise ValueError("an auction needs at least one slot")
        if reserve_price < ZERO:
            raise ValueError("reserve price must not be negative")
        self._ranking = ranking
        self._pricing = pricing
        self._slots = slots
        self._reserve = reserve_price
        self._bidders: list[Bidder] = []
        self._weights: dict[Bidder, Decimal] = {}

    @property
    def bidders(self) -> tuple[Bidder, ...]:
        return tuple(self._bidders)

    def register(self, bidder: Bidder, weight: Decimal = UNIT) -> Bidder:
        if bidder not in self._bidders:
            self._bidders.append(bidder)
        self.set_weight(bidder, weight)
        return bidder

    def set_weight(self, bidder: Bidder, weight: Decimal) -> None:
        if weight <= 0:
            raise ValueError("weight must be positive")
        self._weights[bidder] = weight

    def search(self, term: str) -> AuctionResult:
        key = SearchTerm(term)
        bids = (bid for bidder in self._bidders if (bid := bidder.bid_for(key)))
        ranking = self._ranking.rank(filter(self._admits, bids), self._weights)
        awards = tuple(
            SlotAward(position + 1, ranked.bid, self._price(ranking, position))
            for position, ranked in enumerate(ranking[: self._slots])
        )
        return AuctionResult(key, awards)

    def _admits(self, bid: Bid) -> bool:
        return not bid.is_exhausted and bid.effective_bid >= self._reserve

    def _price(self, ranking: Sequence[RankedBid], position: int) -> Money:
        """No bidder ever pays more than it offered, nor less than the reserve."""
        offered = ranking[position].bid.effective_bid
        return min(offered, max(self._reserve, self._pricing.price(ranking, position)))
