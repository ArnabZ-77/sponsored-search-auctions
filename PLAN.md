# Sponsored Search Auctions — Implementation Plan

Take-home for WheelOps. Time box: 3 hours. Language: Python 3.12+ / pytest, no runtime dependencies.

## 1. What the brief asks for

| Requirement (from the brief) | Where it lands |
|---|---|
| Two ranking mechanisms: rank by bid (`w=1`), rank by score (`s = w·b`) | `ranking.py` — `RankByBid`, `RankByScore` |
| Two pricing mechanisms: GFP (pay own bid), GSP (pay `s(j+1)/w(j)`) | `pricing.py` — `GeneralizedFirstPrice`, `GeneralizedSecondPrice` |
| All four mechanisms | any ranking × any pricing, composed in `AuctionHouse` |
| Auctioneer fixes ranking, pricing and weights before auctions run | `AuctionHouse(ranking, pricing, slots, reserve)`, `register(bidder, weight)` |
| Bidder holds a private set of bids: term, max price, budget | `Bidder.place_bid`, `Bid` keeps price/budget behind its interface |
| Bidder may change max price and budget over time | `Bid.update(...)`, `Bidder.place_bid` on an existing term |
| Auction runs on each search for a term with ≥1 registered bidder | `AuctionHouse.search(term)` |
| Charge only on click; the user need not click | `AuctionResult.click(position)` |
| Budget is never overrun | effective-bid model + `Bid.charge` guard (see §3) |
| Fixed number of slots | `slots` on `AuctionHouse` |
| One slot per bidder per auction | one `Bid` per `(Bidder, SearchTerm)` by construction |
| Unit + integration tests, no UI/API | `tests/unit`, `tests/integration` |

## 2. Research that shaped the design

**The brief is Lahaie (2006), *An Analysis of Alternative Slot Auction Designs for Sponsored Search*.**
Its §2.2 fixes the edge cases the brief leaves silent:

- GSP's runner-up is the **next-ranked participant**, not the next slot winner. With more bidders
  than slots, the last slot is priced off the first bidder who won nothing. Only the bidder
  ranked last overall pays zero — Lahaie notes this is "effectively a reserve price of zero" and
  real engines charge a non-zero reserve, so the reserve is configurable (default 0).
- Ties break by a permutation fixed in advance, "consistent with … order of arrival". We use
  registration order via Python's stable sort.
- GFP pays the own bid under **both** ranking rules; non-winners always pay zero.

**Key insight:** under rank-by-bid `w = 1`, so `s(j+1)/w(j)` collapses to `b(j+1)` and GFP is
`s(j)/w(j) = b(j)`. Both pricing rules are written once over scores and weights and work unchanged
under both rankings. Four mechanisms are 2 + 2 classes, not 4.

**Budgets are the part Lahaie does not solve** (footnote 5: "we do not model budget constraints").
Díaz, Giotis, Kirousis, Markakis & Serna (2013), *On the Stability of GSP Auctions with Budgets*,
defines four budget-aware variants and proves which are stable. We adopt **BCSP(best offer)**.

## 3. Budget model — BCSP(best offer), adapted to per-click charging

Each bid competes with its **effective bid** `min(max_price, remaining_budget)`; ranking and
pricing operate on effective bids. Consequences:

- Budget safety is a theorem, not a check:
  `price ≤ s(j+1)/w(j) ≤ s(j)/w(j) = effective_bid(j) ≤ remaining_budget(j)`.
- No over-exclusion: a bidder with ₹0.10 left and a ₹1.00 max price still competes, capped at ₹0.10.
- It is the mechanism whose price is "the minimum bid required to secure the slot" — the brief's
  own definition of GSP — and it always has a Nash equilibrium with an envy-free assignment
  (Díaz et al., Thm 5).
- "Advertisers who have not exhausted their budgets" ⇔ `effective_bid > 0`.

Clicks re-validate at charge time: repeated clicks on one result can drain a budget mid-result,
in which case the click raises `BudgetExhausted` and nothing is charged. The bid then drops out of
later auctions automatically.

Rounding: prices are `Decimal`, never `float`. `s(j+1)/w(j)` is a division, so the result is rounded
half-up to the cent, then clamped to `min(offered, max(reserve, price))` in exactly one place
(`AuctionHouse._price`) so the invariant holds for any pricing strategy.

## 4. Architecture

```
src/sponsored_search/
  money.py     Money value object (Decimal, cent precision)
  bidding.py   SearchTerm, Bid (private price/budget, spend ledger), Bidder, BudgetExhausted
  ranking.py   RankedBid, RankingStrategy (template) → RankByBid, RankByScore
  pricing.py   PricingStrategy → GeneralizedFirstPrice, GeneralizedSecondPrice
  auction.py   SlotAward, AuctionResult (immutable, clickable), AuctionHouse (auctioneer)
tests/
  unit/         money, bidding, ranking, pricing
  integration/  the 2×2 mechanism matrix, budgets & clicks, bids changing over time, invariants
```

Patterns, each earning its place:

- **Strategy ×2** — ranking and pricing are independent axes; mechanisms are compositions.
- **Template Method** — `RankingStrategy.rank` owns sort + tie-break; subclasses supply `weight_of`.
- **Null Object** — `RankByBid.weight_of` returns 1, which is *why* the unified pricing works.
- **Value Object** — `Money`, `SearchTerm` (normalized on construction).
- **Immutable result** — `AuctionResult`/`SlotAward` are frozen; clicks charge the bid, never mutate the result.
- **Encapsulation** — the engine only ever asks a bid `effective_bid` / `charge(price)`; max price and budget stay private to the bidder, as the brief requires.

## 5. Build order (runnable after every step)

- [x] 1. `Money`, `SearchTerm`, `Bid`, `Bidder`
- [x] 2. `RankByBid` + `GeneralizedFirstPrice` + fixed slots → first end-to-end auction
- [x] 3. `GeneralizedSecondPrice` with next-participant rule and reserve
- [x] 4. weights + `RankByScore` → all four mechanisms by composition
- [x] 5. `AuctionResult.click` → pay-per-click with spend ledger
- [x] 6. effective-bid budget model + `BudgetExhausted` guard
- [x] 7. unit tests: money, bidding, ranking, pricing
- [x] 8. integration tests: parametrized 2×2 matrix, worked examples, budgets, dynamics
- [x] 9. invariant tests (randomized): price ≤ bid, spend ≤ budget, one slot per bidder, monotonicity, RBB ≡ RBR under equal weights, GSP ≤ GFP
- [x] 10. `demo.py` + `README.md` (how to run, design, scope decisions)

## 6. Explicitly out of scope (deliberate)

- Click-through-rate modelling (slot view probability γ_j) — clicks are an input here, per the brief
- Persistence, REST API, UI — excluded by the brief
- Concurrency / thread safety — first extension point, noted in README
- VCG pricing — a natural third `PricingStrategy`; the design accommodates it without change
- Budgets shared across keywords — the brief scopes budget to a single bid
- Bid throttling / pacing across the day — the brief's wording is the non-throttling model

## 7. Sources

- Lahaie, *An Analysis of Alternative Slot Auction Designs for Sponsored Search*, EC'06
- Díaz, Giotis, Kirousis, Markakis, Serna, *On the Stability of Generalized Second Price Auctions with Budgets*, 2013
- Edelman, Ostrovsky, Schwarz, *Internet Advertising and the Generalized Second-Price Auction*, AER 2007
- Qin, Chen, Liu, *Sponsored Search Auctions: Recent Advances and Future Directions*
