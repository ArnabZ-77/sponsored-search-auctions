from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from operator import attrgetter

from .bidding import Bid, Bidder
from .money import CENT, Money

UNIT = Decimal(1)
Weights = Mapping[Bidder, Decimal]
BY_SCORE = attrgetter("score.amount")


@dataclass(frozen=True, slots=True)
class RankedBid:
    bid: Bid
    weight: Decimal
    offer: Money
    score: Money


class RankingStrategy(ABC):
    def rank(self, bids: Iterable[Bid], weights: Weights, floor: Money = CENT) -> list[RankedBid]:
        """Bids offering at least `floor`, highest score first; ties keep the order the bids arrived."""
        ranked = [scored for bid in bids if (scored := self._score(bid, self.weight_of(bid, weights))).offer >= floor]
        ranked.sort(key=BY_SCORE, reverse=True)
        return ranked

    @abstractmethod
    def weight_of(self, bid: Bid, weights: Weights) -> Decimal: ...

    @staticmethod
    def _score(bid: Bid, weight: Decimal) -> RankedBid:
        offer = bid.effective_bid
        return RankedBid(bid, weight, offer, offer * weight)


class RankByBid(RankingStrategy):
    def weight_of(self, bid: Bid, weights: Weights) -> Decimal:
        return UNIT


class RankByScore(RankingStrategy):
    def weight_of(self, bid: Bid, weights: Weights) -> Decimal:
        return weights.get(bid.bidder, UNIT)
