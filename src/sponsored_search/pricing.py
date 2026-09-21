from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .money import ZERO, Money
from .ranking import RankedBid


class PricingStrategy(ABC):
    @abstractmethod
    def price(self, ranking: Sequence[RankedBid], position: int) -> Money: ...


class GeneralizedFirstPrice(PricingStrategy):
    def price(self, ranking: Sequence[RankedBid], position: int) -> Money:
        return ranking[position].bid.effective_bid


class GeneralizedSecondPrice(PricingStrategy):
    """Slot j pays s(j+1) / w(j); the runner-up is the next-ranked participant, slot or no slot."""

    def price(self, ranking: Sequence[RankedBid], position: int) -> Money:
        runner_up = ranking[position + 1].score if position + 1 < len(ranking) else ZERO
        return runner_up / ranking[position].weight
