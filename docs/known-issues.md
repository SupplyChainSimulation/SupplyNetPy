# Known Issues and Planned Work

This page lists known issues, current limitations, and planned improvements for upcoming versions of **SupplyNetPy**.


## Known Issues

- ⚠️ **Loops in a Supply Chain**: The library does not check for loops in the network. It is possible to create a supply chain with loops, for example, when two distribution centers are connected to overcome shortages during supply.
- ⚠️ **Simultaneous Events**: When multiple events are scheduled at the same time (e.g., at time t=10), they are executed sequentially, one after another. SupplyNetPy is built on SimPy and executes events according to event IDs (as in SimPy). For deterministic simulations, the same output is generated for each run.
- ⚠️ **Simulation Parallelization**: Currently, SupplyNetPy does not support parallelizing the simulation model.
- ⚠️ **Real-Time Simulation**: Real-time simulation is not supported.
- ⚠️ **Link disruption only blocks new orders**: When a `Link` becomes inactive, any shipment already dispatched over it continues to completion — SupplyNetPy does not currently interrupt in-transit deliveries on a disrupted link. Only *new* replenishment orders are blocked until the link recovers. Supplier-selection policies (`SelectFirst`, `SelectAvailable`, `SelectCheapest`, `SelectFastest`) filter out disrupted links by default, so they will prefer active suppliers when one exists; if every link is down, the policy still returns a supplier (so callers don't need to handle `None`), and the dispatch gate at `process_order` blocks it until a link recovers. In `"fixed"` mode, if the locked supplier's link is temporarily disrupted, the policy routes around it through an active alternative and resumes the lock once the link recovers.

---

## Planned Work

- **Case Studies**: Real-world supply chain models.
- **Logistics Operations**: Geographic map locations, CO₂ calculations, and fleet management.
- **Simulation Parallelization**: To enable faster execution of the model and support real-time simulation.
- **Simulation-Based Optimization (SBO)**: Integration of optimization methods from Python's SciPy library to support SBO.

> Note: Disruption modeling for both nodes (warehouses, factories, retailers, etc.) and links (transport routes) is already built into SupplyNetPy and is *not* on the planned-work list. You can configure disruptions in two ways:
>
> - **Random** — set `failure_p` on a `Node` (or its equivalent on a `Link`) to give it a probability of failing at each tick.
> - **Scheduled** — set `node_disrupt_time` and `node_recovery_time` to make the node go offline at fixed intervals and come back after a fixed delay.
>
> On top of that, the `disruption_impact` setting on a node controls what happens to the *goods on the shelf* when a disruption begins:
>
> - `"destroy_all"` — every unit at the node is lost (e.g., a fire at a warehouse).
> - `"destroy_fraction"` — a portion of the stock is lost. The portion is given by `disruption_loss_fraction`, which can be either a fixed number between 0 and 1 (e.g., `0.3` for 30%) or a small Python function that returns a different value each time, if you want randomized losses.
> - A custom Python function — for any other rule (contamination of certain batches, partial spoilage, capacity damage, etc.).
>
> The amount destroyed and its monetary value are recorded automatically as `node.stats.destroyed_qty` and `node.stats.destroyed_value`, and the value is subtracted from profit, so the financial impact appears in the simulation results without any extra bookkeeping.
>
> If you want repeatable simulation runs (for example, to compare two policies fairly under the *same* sequence of random failures), either pass an `rng` argument when you create a node or link, or call `scm.set_seed(n)` once before building the network.