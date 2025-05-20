<style>
    h3.classhead{
        padding:15px; 
        background-color:#cccccc;
        border: 1px solid #bbbbbb;
        border-radius: 5px;
    }
</style>

## SupplyNetPy `Components.core` Module

The `Components.core` module provides the foundational building blocks for modeling and simulating supply chain networks in SupplyNetPy. It defines key classes representing entities and their interactions within a supply chain.

### Overview

This module includes the following primary classes:

| Class                 | Description                                                                                      |
|-----------------------|--------------------------------------------------------------------------------------------------|
| `RawMaterial`         | Represents a raw material used as input in the supply chain.                                     |
| `Product`             | Represents a product in the supply chain.                                                        |
| `Inventory`           | Inventory maintained by any node, tracking stock levels and related operations.                  |
| `PerishableInventory` | Specialized inventory class for handling perishable goods with shelf-life tracking.              |
| `Node`                | Generic node in the supply chain network. (ex. retailer, warehouse, demand)                      |
| `Link`                | Transportation or connection link between two nodes in the supply chain.                         |
| `Supplier`            | Node representing a supplier of raw materials or products.                                       |
| `Manufacturer`        | Node representing a manufacturer that manufactures a product.                                    |
| `InventoryNode`       | Node that maintains inventory, such as a warehouse, distributor, or retailer.                    |
| `Demand`              | Represents demand at a specific node in the network.                                             |

### Usage

To model a supply chain, instantiate these classes and configure their attributes and relationships. Each class provides methods for setting properties and computing performance metrics.

---

## API Reference

### Classes
- [`RawMaterial`](#rawmat)
- [`Product`](#product)
- [`Link`](#link)
- [`Node`](#node)
- [`Inventory`](#inventory)
- [`PerishableInventory`](#perishinv)
- [`Supplier`](#supplier)
- [`Manufacturer`](#manufacturer)
- [`InventoryNode`](#inventorynode)
- [`Demand`](#demand)

---

<div id="rawmat">
<h3 class="classhead">Class RawMaterial</h3></div>
:::SupplyNetPy.Components.core.RawMaterial

---

<div id="product">
<h3 class="classhead">Class Product</h3></div>
:::SupplyNetPy.Components.core.Product

---

<div id="link">
<h3 class="classhead">Class Link</h3></div>
:::SupplyNetPy.Components.core.Link

---

<div id="node">
<h3 class="classhead">Class Node</h3></div>
:::SupplyNetPy.Components.core.Node

---

<div id="inventory">
<h3 class="classhead">Class Inventory</h3></div>
:::SupplyNetPy.Components.core.Inventory

---

<div id="perishinv">
<h3 class="classhead">Class PerishableInventory</h3></div>
:::SupplyNetPy.Components.core.PerishableInventory

---

<div id="supplier">
<h3 class="classhead">Class Supplier</h3></div>
:::SupplyNetPy.Components.core.Supplier

---

<div id="manufacturer">
<h3 class="classhead">Class Manufacturer</h3></div>
:::SupplyNetPy.Components.core.Manufacturer

---

<div id="inventorynode">
<h3 class="classhead">Class InventoryNode</h3></div>
:::SupplyNetPy.Components.core.InventoryNode

---

<div id="demand">
<h3 class="classhead">Class Demand</h3></div>
:::SupplyNetPy.Components.core.Demand

---