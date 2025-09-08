# Known Issues and Planned Work

This page lists known issues, current limitations, and planned improvements for upcoming versions of **SupplyNetPy**.

## Known Issues

- ⚠️ **Loops in a Supply Chain**: The library does not check for loops in the network. It is possible to create a supply chain with loops, for example, when two distribution centers are connected to overcome shortages during supply.  
- ⚠️ **Simultaneous Events**: When multiple events are scheduled at the same time (e.g., at time t=10), they are executed sequentially, one after another. SupplyNetPy is built on SimPy and executes events according to event IDs (as in SimPy). For deterministic simulations, the same output is generated for each run.  
- ⚠️ **Simulation Parallelization**: Currently, SupplyNetPy does not support parallelizing the simulation model.  
- ⚠️ **Real-Time Simulation**: Real-time simulation is not supported.  

## Planned Work

- ✅ **Case Studies**: Example supply chain models from pharma, retail, and e-commerce domains.  
- ✅ **Logistics Operations**: Geographic map locations, CO₂ calculations, and fleet management.  
- ✅ **Node/Link Disruption**: For resilience and risk assessment, this feature will interrupt events impacted by disruptions (earthquakes, natural calamities, pandemics, etc.).  
- ✅ **Simulation Parallelization**: To enable faster execution of the model and support real-time simulation.  
- ✅ **Simulation-Based Optimization (SBO)**: Integration of optimization methods from Python's SciPy library to support SBO.  