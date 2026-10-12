# Known Issues and Planned Work

This page lists known issues, current limitations, and planned improvements for upcoming versions of **SupplyNetPy**.


## Known Issues

* ⚠️ **Loops in a supply chain.** The library does not check for loops in the network. It is possible to create a supply chain with loops, for example when two distributors are linked to each other to cover shortages.
* ⚠️ **Simultaneous events.** When several events are due at the same time (for example at time 10), they are carried out one after another. SupplyNetPy is built on SimPy and carries out such events in SimPy's order, by event ID. For simulations without randomness, every run gives the same output.
* ⚠️ **Simulation parallelization.** SupplyNetPy does not currently run a simulation in parallel.
* ⚠️ **Simulating in real time.** Running a simulation in step with the real clock is not supported.
* ⚠️ **A link disruption only blocks new orders.** When a `Link` is disrupted, orders already in transit over it still arrive. SupplyNetPy does not currently stop orders in transit on a disrupted link. Only *new* replenishment orders are not sent until the link recovers. The supplier-selection policies (`SelectFirst`, `SelectAvailable`, `SelectCheapest`, `SelectFastest`) skip suppliers whose site or link is disrupted, so they choose a supplier that can take the order when there is one. If no supplier can take it, the order is not placed, and the replenishment policy checks its inventory position again as soon as a supplier or a link recovers. In `"fixed"` mode, while the remembered supplier or the link to it is disrupted, the policy uses another supplier, and goes back to the remembered supplier once it recovers.

---

## Planned Work

* **More case studies.** Models of real supply chains.
* **Logistics operations.** Geographic map locations, CO₂ calculations, and fleet management.
* **Simulation parallelization.** Faster runs of the model, and support for simulating in real time.
* **Simulation based optimization (SBO).** Optimization methods from Python's SciPy library, to support SBO.
