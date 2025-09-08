# SupplyNetPy: Complex Hybrid Network Example

This example demonstrates how to build and simulate a multi‑echelon, hybrid supply chain with different replenishment policies in **SupplyNetPy**.

![Newsvendor](img/bread_sc.png)

## Goals

* Creating a network with multiple raw materials, suppliers, a manufacturer, two distributors, and several retailers.
* Mix replenishment policies (\`SS\`, \`RQ\`, \`Periodic\`).
* Include hybrid connections (ordering from multiple distributors).

## Key Concepts Used

* **Products, Raw Materials**: Class `Product` used to create a product, Bread, with some shelf life, `RawMaterial` is used to create raw materials (dough, sugar, yeast)
* **Nodes**: Clasees `Supplier`, `Manufacturer`, `InventoryNode` are used to create suppliers,  bakery (factory), distributors, and retailers (cake shops).
* **Links**: Class `Link` is used to link different nodes in the network
* **Policies**:
    * `SSReplenishment`: order up to **S** when inventory <= **s**
    * `RQReplenishment`: reorder point **R**, fixed order quantity **Q**
    * `PeriodicReplenishment`: review every **T**, order **Q**.
* **Perishability**: `inventory_type` for all nodes is `perishable`, and parameter `shelf_life` is passed. 

## Full Example

> This script constructs a hybrid network with two distributors and five retailers, then runs a short simulation.

```python
{% 
    include "../examples/py/hybrid_big_sc.py" 
    start="#pyscript-st"
    end="#pyscript-en"
%}
```

## Sample Output

```
{% 
    include "../examples/py/hybrid_big_sc.py" 
    start="#out-st"
    end="#out-en"
%}
```


## Suggested Experiments

* Vary `policy_param` values (`s/S`, `R/Q`, `T/Q`).
* Change `lead_time` lambdas and link costs.
* Switch retailer `inventory_type` and `shelf_life` to study perishability.
* Add/remove cross‑links to test resilience.

## Notes

* Keep node IDs unique.
* Ensure `product_buy_price` ≤ upstream `product_sell_price` where applicable.
* Use consistent time units across processing, lead times, and review periods.
