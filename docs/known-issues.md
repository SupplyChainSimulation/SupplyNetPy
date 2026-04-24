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

> Note: Node and link disruption (`failure_p`, `node_disrupt_time`, `node_recovery_time` on `Node`; equivalents on `Link`) is already supported and is not planned work. Pass an `rng` argument, or call `scm.set_seed(n)` before building the network, to make disruption draws reproducible.