# Sponsored Search Auctions

A small, fully tested sponsored-search auction system implementing the four mechanisms from the brief:
two ranking rules (**rank by bid**, **rank by score**) composed with two pricing rules
(**generalized first price**, **generalized second price**), with per-click charging that can never
overrun a bidder's budget.

Pure Python 3.12+, no runtime dependencies.

## Run

```bash
pip install pytest
python -m pytest          # 174 tests, < 1 s
python demo.py            # the same market under all four mechanisms, with clicks and budgets
```

## How it fits together

```
Bidder ──holds──▶ Bid (search term, max price, budget)   private to the bidder
AuctionHouse(ranking, pricing, slots, reserve)           the auctioneer
   .register(bidder, weight)                             weights w_j are the auctioneer's
   .search(term) ──▶ AuctionResult(awards)               one auction per search
                        .click(position)                 charges that slot's price per click
```

`search()` collects every registered bidder's bid for the term, drops exhausted ones, ranks them,
and prices the top `slots` of the ranking. Nothing is charged until a user clicks.

### The four mechanisms are 2 + 2 classes, not 4

| | `GeneralizedFirstPrice` | `GeneralizedSecondPrice` |
|---|---|---|
| `RankByBid` (w = 1) | pays own bid | pays next bid |
| `RankByScore` (s = w·b) | pays own bid | pays s(j+1) / w(j) |

Both pricing rules are written once, over scores and weights. Under rank-by-bid the weight is 1, so
`s(j+1)/w(j)` *is* `b(j+1)` and `s(j)/w(j)` *is* `b(j)` — the same code produces all four cells.
`RankByBid` is a null-object weight; `RankByScore` looks the weight up. Adding a third pricing rule
(e.g. VCG) or a third ranking rule is one new class and touches nothing else.

### Rules the brief leaves implicit (and where they come from)

The brief follows Lahaie, *An Analysis of Alternative Slot Auction Designs for Sponsored Search*
(EC'06), which settles the edge cases:

- **GSP's runner-up is the next-ranked *participant*, not the next slot winner.** With more bidders
  than slots, the last slot is priced off the first bidder who won nothing (`test_last_slot_is_priced_off_the_first_bidder_who_won_nothing`).
- **Only the bidder ranked last overall pays zero** — unless a reserve price is set, in which case
  the reserve is the floor and bids below it do not participate.
- **Ties break by registration order**, the arrival-based fixed permutation Lahaie describes.
- **GFP pays the own bid under both rankings; non-winners never pay.**

### Budgets: the effective-bid model

Lahaie explicitly does not model budgets. For that we follow Díaz, Giotis, Kirousis, Markakis &
Serna, *On the Stability of GSP Auctions with Budgets* (2013), and use their **best-offer**
mechanism, adapted to per-click charging:

> A bid competes with its **effective bid** `min(max price, remaining budget)`.

That single line gives every guarantee the brief asks for:

- **The budget is never overrun** — by construction, not by a check:
  `price ≤ s(j+1)/w(j) ≤ s(j)/w(j) = effective bid ≤ remaining budget`.
- **"Advertisers who have not exhausted their budgets"** ⇔ effective bid > 0.
- **No over-exclusion.** A bidder with ₹0.10 left and a ₹1.00 max price still competes, capped at
  ₹0.10 — the naive `remaining ≥ max price` filter would wrongly drop it.
- The price is "the minimum bid required to secure the slot", which is exactly the brief's definition
  of second pricing; and the mechanism always has a Nash equilibrium with an envy-free assignment
  (Díaz et al., Thm. 5).

A click re-validates at charge time, because repeated clicks on one result can drain a budget
mid-result. An unaffordable click raises `BudgetExhausted` and charges nothing; the bid then sits out
later auctions until the bidder tops it up.

### Money

Prices are `Decimal` at cent precision, never `float`. `s(j+1)/w(j)` is a division, so the result is
rounded half-up to the cent; `AuctionHouse._price` then clamps every price to
`min(offered, max(reserve, price))` in one place, so the "never pay more than offered" invariant holds
for any pricing strategy anyone adds later.

## Design decisions

- **Budget belongs to the bid**, per the brief ("each such bid is associated with a search term, a
  maximum bid price and a budget"). Max price and budget are private to the `Bid`; the auction only
  ever asks `effective_bid` and `charge(price)`.
- **One slot per bidder** is structural: a bidder holds exactly one bid per search term, so it can
  appear in a ranking at most once. Re-bidding on a term updates that bid and preserves its spend.
- **Results are immutable.** `AuctionResult`/`SlotAward` are frozen snapshots; clicking charges the
  underlying bid but the awarded prices never change.
- **Every search is a fresh auction on current state**, so bid and budget changes take effect on the
  next search — the "boost your bid before Valentine's Day" scenario in the brief.

## Tests

- `tests/unit` — `Money` arithmetic and rounding, bid/budget bookkeeping, each ranking rule, each
  pricing rule in isolation.
- `tests/integration/test_mechanisms.py` — the 2×2 matrix with hand-verified prices, shared
  properties parametrized over all four mechanisms, reserve prices, the classic
  Edelman–Ostrovsky–Schwarz (AER 2007) example.
- `tests/integration/test_budget.py` — exhaustion, capping, top-ups, clicks refused mid-result.
- `tests/integration/test_dynamics.py` — bids, budgets and weights changing between auctions.
- `tests/integration/test_invariants.py` — randomized markets checking, for every mechanism: spend ≤
  budget under arbitrary click sequences, price ≤ offer, one slot per bidder, awards ≤ slots,
  rank-by-bid ≡ rank-by-score under equal weights, GSP ≤ GFP per slot, and raising your bid never
  lowers your position.

## Deliberately out of scope

- Click-through-rate modelling (slot view probability): clicks are an input to this system, per the brief.
- Persistence, REST API, UI: excluded by the brief.
- Concurrency: the model is single-threaded; `AuctionHouse` is the obvious place to add locking.
- VCG pricing: a natural third `PricingStrategy`, not requested.
- Budgets shared across keywords, and pacing/throttling within a day: the brief scopes budget to a
  single bid and describes the non-throttling model.

## Layout

```
src/sponsored_search/
  money.py     Money value object
  bidding.py   SearchTerm, Bid, Bidder, BudgetExhausted
  ranking.py   RankingStrategy → RankByBid, RankByScore
  pricing.py   PricingStrategy → GeneralizedFirstPrice, GeneralizedSecondPrice
  auction.py   SlotAward, AuctionResult, AuctionHouse
tests/         unit/ and integration/
demo.py        runnable walk-through
PLAN.md        the plan this was built from, including research notes
```
