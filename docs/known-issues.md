<style>
  /* Known issues only: undo the grey h3 banner from css/extra.css, as on the release history page */
  h3 { padding: 0; margin: 1em 0 0.4em; border: none; border-radius: 0; background: none; }
</style>

# Known Issues and Planned Work

This page lists known issues, current limitations, and planned improvements for upcoming versions of **SupplyNetPy**.


## Known Issues

* ⚠️ **Loops in a supply chain.** The library does not check for loops in the network. It is possible to create a supply chain with loops, for example when two distributors are linked to each other to cover shortages.
* ⚠️ **Simultaneous events.** When several events are due at the same time (for example at time 10), they are carried out one after another. SupplyNetPy is built on SimPy and carries out such events in SimPy's order, by event ID. For simulations without randomness, every run gives the same output.
* ⚠️ **A run stops just before its end time.** A run with `simulate_sc_net(..., sim_time=T)` or `env.run(until=T)` carries out every event due before time T, but not the events due at exactly time T. For example, a run with `sim_time=360` does not see a customer order or an expiry due at time 360. To include the events at time T, run to a slightly later time, such as T + 1. This is how SimPy works. The [pharmacy case study](case_study_pharma.md) runs to T + 1 for this reason, so that it counts the same days as the paper it reproduces.
* ⚠️ **Simulation parallelization.** SupplyNetPy does not currently run a simulation in parallel.
* ⚠️ **Simulating in real time.** Running a simulation in step with the real clock is not supported.
* ⚠️ **A link disruption only blocks new orders.** When a `Link` is disrupted, orders already in transit over it still arrive. SupplyNetPy does not currently stop orders in transit on a disrupted link. Only *new* replenishment orders are not sent until the link recovers. The supplier-selection policies (`SelectFirst`, `SelectAvailable`, `SelectCheapest`, `SelectFastest`) skip suppliers whose site or link is disrupted, so they choose a supplier that can take the order when there is one. If no supplier can take it, the order is not placed, and the replenishment policy checks its inventory position again as soon as a supplier or a link recovers. In `"fixed"` mode, while the remembered supplier or the link to it is disrupted, the policy uses another supplier, and goes back to the remembered supplier once it recovers.
* ⚠️ **An order larger than the supplier can hold is never filled.** A supplier sends a replenishment order only when it has all of it, in one shipment. So if a buyer orders more units than its supplier's capacity, the supplier can never hold enough to send the order. The buyer waits for it for ever, and the two are stuck (a deadlock). For example, a distributor that holds at most 100 units can never fill an order of 150 units from a retailer that holds 200. For a manufacturer, count the raw material it needs. A manufacturer that holds 150 units of a product made from 2 units of raw material each can order up to 300 units of that raw material. SupplyNetPy warns about such a pair when the link between them is created, and again if such an order is placed. Until this changes, give each supplier a capacity at least as large as what its buyers can order.

---

## Planned Work

### Next updates

Features and fixes planned for the coming versions of the library.

* **Probability-based supplier selection.** A supplier-selection policy that chooses among the suppliers of a site at random, with a probability for each supplier.
* **Orders in smaller parts.** A buyer will be able to receive a replenishment order in smaller parts as the supplier gets units, or to take only what the supplier has, so that an order larger than the supplier's capacity can still be filled.
* **Checking the whole network.** A check, run before a simulation, that every node is connected, that the settings fit together, and that units flow towards the customers.
* **Perishable raw materials.** Raw materials with manufacturing dates and a shelf life, as many have in reality. For now, SupplyNetPy assumes that raw materials are not perishable, so the inventory of a raw-material supplier and the raw materials a manufacturer holds are always non-perishable.

### Long-term goals

Larger directions for SupplyNetPy, beyond the next few versions.

* **More case studies.** Models of real supply chains.
* **Logistics operations.** Geographic map locations, CO₂ calculations, and fleet management.
* **Simulation parallelization.** Faster runs of the model, and support for simulating in real time.
* **Simulation based optimization (SBO).** Optimization methods from Python's SciPy library, to support SBO.
