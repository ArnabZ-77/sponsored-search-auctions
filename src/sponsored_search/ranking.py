from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from .bidding import Bid, Bidder
from .money import Money

UNIT = Decimal(1)
Weights = Mapping[Bidder, Decimal]


@dataclass(frozen=True)
class RankedBid:
    bid: Bid
    weight: Decimal
    score: Money


class RankingStrategy(ABC):
    def rank(self, bids: Iterable[Bid], weights: Weights) -> list[RankedBid]:
        """Highest score first; ties keep registration order (a fixed, arrival-based permutation)."""
        ranked = [self._score(bid, self.weight_of(bid, weights)) for bid in bids]
        return sorted(ranked, key=lambda ranked_bid: ranked_bid.score, reverse=True)

    @abstractmethod
    def weight_of(self, bid: Bid, weights: Weights) -> Decimal: ...

    @staticmethod
    def _score(bid: Bid, weight: Decimal) -> RankedBid:
        return RankedBid(bid, weight, bid.effective_bid * weight)


class RankByBid(RankingStrategy):
    def weight_of(self, bid: Bid, weights: Weights) -> Decimal:
        return UNIT


class RankByScore(RankingStrategy):
    def weight_of(self, bid: Bid, weights: Weights) -> Decimal:
        return weights.get(bid.bidder, UNIT)
