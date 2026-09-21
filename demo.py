"""Walk-through: one market, four mechanisms, then clicks against a tight budget."""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sponsored_search import (
    AuctionHouse,
    Bidder,
    BudgetExhausted,
    GeneralizedFirstPrice,
    GeneralizedSecondPrice,
    Money,
    RankByBid,
    RankByScore,
)

TERM = "tyre shop software"
MARKET = [("WheelOps", "0.50", "10.00", "1"), ("TyreMax", "0.30", "10.00", "2"), ("Garagio", "0.20", "0.05", "1")]


def build(ranking, pricing) -> AuctionHouse:
    house = AuctionHouse(ranking, pricing, slots=2)
    for name, price, budget, weight in MARKET:
        house.register(Bidder(name), Decimal(weight)).place_bid(TERM, Money.of(price), Money.of(budget))
    return house


print(f"Search term: '{TERM}', 2 slots")
for name, price, budget, weight in MARKET:
    print(f"  {name:<9} max price {price}  budget {budget:>5}  weight {weight}")

for ranking in (RankByBid(), RankByScore()):
    for pricing in (GeneralizedFirstPrice(), GeneralizedSecondPrice()):
        result = build(ranking, pricing).search(TERM)
        awards = ", ".join(f"slot {a.position}: {a.bidder} pays {a.price_per_click}/click" for a in result.awards)
        print(f"\n{type(ranking).__name__:<12} x {type(pricing).__name__:<22} -> {awards}")

print("\nClicks against a tight budget (rank by bid, GSP, WheelOps budget lowered to 0.70):")
house = build(RankByBid(), GeneralizedSecondPrice())
wheelops = house.bidders[0]
wheelops.place_bid(TERM, Money.of("0.50"), Money.of("0.70"))
result = house.search(TERM)
for click in range(1, 5):
    try:
        print(f"  click {click}: charged {result.click(1)}, spent so far {result.awards[0].bid.spent}")
    except BudgetExhausted as refused:
        print(f"  click {click}: refused - {refused}")
print(f"  next search -> {', '.join(f'{a.bidder} pays {a.price_per_click}' for a in house.search(TERM).awards)}")
