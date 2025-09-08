# SupplyNetPy in 10 Minutes

## Installation

SupplyNetPy can be installed using pip:

```sh
pip install supplynetpy
```

## Quick Start: Building a Simple Three-Node Supply Chain

Follow these steps to create and simulate a basic supply chain with a supplier and a manufacturer:

![A three node supply chain.](img/img_two_node_sc.png)

### 1. Import the Library

```python
import SupplyNetPy.Components as scm
```

The `Components` module in SupplyNetPy offers essential building blocks for constructing supply chain networks. It enables us to define supply chain nodes, products, inventory, demand, and the links that connect them. We can easily assemble and customize supply chain models using these constructs to suit particular requirements.

### 2. Create Nodes

Let us create a supplier node in the supply chain that has infinite inventory and can supply any required quantity of product units to a consumer node. The supplier node requires several parameters, including ID, name, and node type. To set it as an infinite supplier, we must specify the node type as `infinite_supplier`.

```python
{% 
    include "../examples/py/intro_simple.py" 
    start="#sup-st"
    end="#sup-en"
%}
```

A distributor or warehouse node that purchases products from a supplier is created below by specifying configurable parameters, including ID, name, inventory capacity, replenishment policy, policy parameters, product buy price, and product sell price. 

```python
{% 
    include "../examples/py/intro_simple.py" 
    start="#dis-st"
    end="#dis-en"
%}
```

[qt]: ## "(Q,T): Replenish inventory every T days with Q units."
[ss]: ## "Continuously monitor inventory; replenish up to S when the level drops below s."
[sssafety]: ## "Reorder-level (s,S) replenishment with safety stock — like (s,S) but considers a predefined safety stock buffer."
[rq]: ## "Replenish a fixed quantity Q whenever an order is placed (RQ policy)."
[periodic]: ## "Replenish at regular periodic intervals (Periodic policy)."

When creating a manufacturer, distributor, wholesaler, or retailer, we must specify the inventory replenishment policy and its parameters.

The SupplyNetPy Components module includes an `InventoryReplenishment` class that can be customized to define specific replenishment policies. Currently, SupplyNetPy supports the following replenishment policies:


- <p> [Reorder-level (s,S)](api-reference/api-ref-core.md#ssreplenish) — continuously monitor inventory and replenish up to S when the level drops below s. Parameters: {s, S} &nbsp;&nbsp; (class `SSReplenishment`) </p>

- <p> [Reorder-level (s,S) with Safety Stock](api-reference/api-ref-core.md#ssreplenish) — reorder-level replenishment that factors in a safety stock buffer. Parameters: {s, S, safety_stock} (`SSReplenishment`) </p>

- <p> [Replenish Quantity (RQ)](api-reference/api-ref-core.md#rqreplenish) — reorder a fixed quantity Q when placing an order. Parameters: {R, Q} (`RQReplenishment`) </p>

- <p> [Replenish Quantity (RQ) with safety stock](api-reference/api-ref-core.md#rqreplenish) — reorder a fixed quantity Q when placing an order. Parameters: {R, Q, safety_stock} (`RQReplenishment`) </p>

- <p> [Periodic (T,Q)](api-reference/api-ref-core.md#periodicreplenish) — replenish inventory every T days with Q units. Parameters: {T, Q} (`PeriodicReplenishment`) </p>

- <p> [Periodic (T,Q) with safety stock](api-reference/api-ref-core.md#periodicreplenish) — replenish inventory every T days with Q units. If safety stock is specified, then when the safety stock level is violated, order Q units in addition to the quantity needed to maintain safety stock levels. Parameters: {T, Q, safety_stock} (`PeriodicReplenishment`) </p>

### 3. Create a Link

A link is created as described below. It is configured using parameters such as transportation cost and lead time. The lead time parameter accepts a generative function that produces random lead times based on a specified distribution. Users can create this function according to their needs or define a constant lead time using a Python lambda function.

```python
{% 
    include "../examples/py/intro_simple.py" 
    start="#ln-st"
    end="#ln-en"
%}
```

### 4. Specify Demand

A demand is created by specifying an ID, name, demand node, order arrival time, and order quantity. The order arrival parameter accepts a generator function that produces random arrival times, while the order quantity parameter takes a generator function that produces random quantities. Users can define a function that models these arrivals and quantities or use Python's lambda function to create a deterministic demand, as shown below. A demand can be created at either a distributor node or a retailer. In this example, we have created a steady demand for 10 daily units at distributor D1.

```python
{% 
    include "../examples/py/intro_simple.py" 
    start="#dem-st"
    end="#dem-en"
%}
```

### 5. Assemble and Simulate the Network

To create and simulate the supply chain, use the `create_sc_net` function to instantiate the supply chain nodes and assemble them into a network. This function adds metadata to the supply chain, such as the number of nodes, and other relevant information, keeping everything organized. It returns a Python dictionary containing all supply chain components and metadata. The `simulate_sc_net` function then simulates the supply chain network over a specified period and provides a log of the simulation run. It also calculates performance measures such as net profit, throughput, and more. Let's use these functions to build and simulate our supply chain.

```python
{% 
    include "../examples/py/intro_simple.py" 
    start="#cr-sim-st"
    end="#cr-sim-en"
%}
```

### 6. Review Results

After the simulation, inspect `supplychainnet` to view performance metrics for the supply chain nodes. By default, the simulation log is displayed in the console and saved to a local file named `simulation_trace.log`, which is located in the same directory as the Python script. Each node in the simulation has its own logger, and logging can be enabled or disabled by providing an additional parameter: `logging=True` or `logging=False` while creating the node. SupplyNetPy uses a global logger referred to as `global_logger`, which allows to show or hide all logs by calling `scm.global_logger.enable_logging()` or `scm.global_logger.disable_logging()`.

Below is an example of a simulation log generated by this program. At the end of the log, supply chain-level performance metrics are calculated and printed. These performance measures are computed for each node in the supply chain and include:

- Inventory carry cost (holding cost)
- Inventory spend (replenishment cost)
- Transportation cost
- Total cost
- Revenue
- Profit

<div id="" style="overflow:scroll; height:600px;">
```
{% 
    include "../examples/py/intro_simple.py" 
    start="#out-st"
    end="#out-en"
%}
```
</div>

To access node performance metrics easily, call `node.stats.get_statistics()`. In this example, the `D1` node level statistics can be accessed with the following code:

```python
{% 
    include "../examples/py/intro_simple.py" 
    start="#node-info-st"
    end="#node-info-en"
%}
```
Here is the output produced by the code mentioned above.
```
{% 
    include "../examples/py/intro_simple.py" 
    start="#node-info-out-st"
    end="#node-info-out-en"
%}
```
---

## Alternative Approach: Using Object-Oriented API

This approach demonstrates how to build and simulate a supply chain using SupplyNetPy's object-oriented API. Instead of passing dictionaries to utility functions, we instantiate supply chain components as Python objects, providing greater flexibility and extensibility. Each node and link is created as an object, and the simulation is managed within a SimPy environment, allowing for more advanced customization and integration with other SimPy-based processes.

```python
{% 
    include "../examples/py/intro_simple.py" 
    start="#alt-st"
    end="#alt-en"
%}
```

This script generates an identical simulation log because the network configuration and demand are deterministic. Final statistics will not be included in the log, as overall supply chain statistics are calculated by the function `simulate_sc_net`. However, node-level statistics will still be available and can be accessed as mentioned earlier. We can proceed to create and simulate the supply chain network using the same functions, `create_sc_net` and `simulate_sc_net`, as demonstrated below.

```python
{% 
    include "../examples/py/intro_simple.py" 
    start="#alt-util-st"
    end="#alt-util-en"
%}
```

 Note that an additional parameter, `env`, is passed to the function `create_sc_net` to create a supply chain network. This is necessary because the SimPy environment (`env`) is now created by us and the same needs to be used for creating the supply chain network and running the simulations.
 