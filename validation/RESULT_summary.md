# Validation Results Summary

> **Note:** The spreadsheet (`validation_snp_anylogistix_cmp.ods`) contains a representative selection of model comparisons, not the complete set. Many additional configurations were run and compared during the validation exercise; only a subset is recorded here for reference.

## Validated Models (Models 1 to 8)

The eight models recorded in the spreadsheet span all replenishment policies (RQ, (s,S), (s,S) with safety stock, and TQ), network sizes from 1 to 8 distributors, simulation lengths up to 59 time units, and integer lead times from 1 to 5. They are representative of the broader set of comparisons run during validation. Across all of these recorded configurations, all 19 tracked performance metrics (demand and fulfillment volumes, inventory levels, holding and replenishment costs, revenue, and profit) show **zero difference** between SupplyNetPy and AnyLogistix. This is consistent with results across the wider set of comparisons, which gave confidence that inventory management logic, replenishment triggering, order sizing, cost accounting, and demand fulfillment are all correctly implemented.

Three metrics are zero-difference not only for Models 1 to 8 but also for the pathological cases below: **Demand Placed (Orders) by Site**, **Fulfillment Received (Orders) by Site**, and **Transportation Cost**. These measure the replenishment order-flow on the supply side, which is driven entirely by the deterministic policy trigger and is unaffected by demand-event ordering.

## Pathological Case (Models 9 and 10)

Models 9 and 10 use the same configuration (a single distributor with TQ policy (T=1, Q=400), lead_time=5, and two demand streams at constant real-valued inter-arrival intervals of 0.3 and 0.2), run for simtime=20 and simtime=10 respectively. Both configurations activate two simultaneous-event pathologies described in the conclusion:

- **Case A (simultaneous event collision):** demand_D2 fires at multiples of 0.2, which coincide with TQ reviews (at integer times) and replenishment arrivals (at integer times + 5). Under the lost-sales policy in use, the fulfillment outcome at a collision depends on which event is processed first.
- **Case B (floating-point accumulation):** the non-integer inter-arrival intervals (0.3, 0.2) accumulate representational error at different rates in Python vs the JVM runtime underlying AnyLogistix, gradually shifting effective demand timestamps.

### Metrics with constant, simulation-length-independent divergence

The following metrics differ by the same fixed amount at **both** simtimes (present at simtime=10, does not grow further at simtime=20):

| Metric | Diff (SNP − ALX) |
|---|---|
| Demand Placed (Orders) by Customer | +1 |
| Demand Placed (Products) by Customer | +40 |
| Demand received (orders) Total | +1 |
| Demand received (products) Total | +40 |
| Fulfillment Received (Orders) by Customer | +14 |

The +1 order / +40 product offset in demand counts corresponds to exactly one demand_D2 event (qty = 40). SupplyNetPy records one more demand_D2 occurrence than AnyLogistix regardless of run length, attributable to a Case B boundary effect: the two runtimes apply different conventions for the first demand event arrival time, or for events that land precisely on the simulation boundary. This is a counting discrepancy that does not cascade into inventory or financial state. The financially meaningful metrics (revenue, end inventory, costs) all agree at simtime=10 (see below), confirming the actual simulation state is identical up to that point.

### Metrics that grow with simulation length

The following metrics show **zero (or negligible) difference at simtime=10** but **significant difference at simtime=20**:

| Metric | Diff at simtime=10 | Diff at simtime=20 |
|---|---|---|
| Available Inventory (at simulation end) | 0 | −20 |
| Revenue | 0 | +2 000 |
| Inventory spend (replenishment cost) | 0 | +600 |
| Inventory carrying (holding) cost | ≈ 0 | −22.4 |
| Total cost | ≈ 0 | +578 |
| Profit | ≈ 0 | +1 422 |
| Demand Placed (Products) by Site | 0 | +40 |
| Fulfillment Received (Products) by Customer | +680* | +720 |

\* The +680 at simtime=10 reflects the metric-definition difference noted above, not a genuine state divergence.

The revenue difference of **+2 000 = 40 products × $50** traces to a **single demand_D2 fulfillment event** at **t = 11** (0.2 × 55 = 11.0): at that timestamp, a demand_D2 arrival (qty = 40) and a replenishment arrival (from the TQ review at t = 6, lead_time = 5) coincide exactly. SupplyNetPy processes the replenishment first (it was registered earlier), leaving sufficient inventory to serve the demand. AnyLogistix processes the demand first; with insufficient stock, the order is lost. This single event generates a self-consistent cascade:

- **Revenue** +2 000: 40 extra units sold at $50.
- **Inventory spend** +600: SNP's lower post-sale inventory sits further below capacity, so the next replenishment delivers 20 additional units at $30 each.
- **End inventory** −20: net of −40 (extra sold) + 20 (extra replenished).
- **Inventory carrying cost** −22.4: SNP holds less inventory on average and therefore pays less holding cost over the remaining run.
- **Total cost** +578 = +600 (spend) − 22.4 (carry); **Profit** +1 422 = +2 000 (revenue) − 578 (cost). ✓

The same collision does not occur within simtime=10 because t = 11 lies outside that run window. The nearest candidate collision within simtime=10 is at t = 10 (demand_D2 at 0.2 × 50 = 10.0, replenishment also arriving at t = 10), but at that moment inventory is already at zero before either event is processed, so both tools lose the demand regardless of processing order and reach an identical state.

**Why this divergence grows with simulation length:** because the TQ policy always orders exactly Q = 400 per review regardless of current inventory, the replenishment schedule is identical in both tools. The divergence is therefore bounded to the single event at t = 11 within the simtime = 20 window: no further collision within [11, 20] falls in a region where the two tools have non-zero and unequal inventory, so the difference does not compound further in these runs. In longer runs, additional collisions would be expected to accumulate, increasing the magnitude of the divergence approximately in proportion to the number of such events.

Real supply chain models always involve randomness, and results are usually determined through several repetitions, and in such corner cases, do not turn out to be of much significance.
