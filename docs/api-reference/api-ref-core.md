<style>
    h3.classhead{
        padding:15px; 
        background-color:#cccccc;
        border: 1px solid #bbbbbb;
        border-radius: 5px;
    }
</style>

# SupplyNetPy `Components.core` Module

The `Components.core` module provides the foundational building blocks for modeling and simulating supply chain networks in SupplyNetPy. It defines key classes representing entities and their interactions within a supply chain.

# Overview:

This module includes the following primary classes:

| Class                           | Description                                                                                   |
|---------------------------------|-----------------------------------------------------------------------------------------------|
| [`NamedEntity`](#namedentity)   | Base class providing a standard string representation using `name` or `ID`.                   |
| [`InfoMixin`](#infomixin)       | Mixin that provides methods for retrieving object info and statistics as dictionaries.        |
| [`Statistics`](#statistics)     | Class for tracking and summarizing performance metrics and statistics.                        |
| [`RawMaterial`](#rawmat)        | Represents a raw material used as input in the supply chain.                                  |
| [`Product`](#product)           | Represents a product in the supply chain.                                                     |
| [`InventoryReplenishment`](#inventoryreplenishment)    | Abstract base class for replenishment policies.                        |
| [`SSReplenishment`](#ssreplenish)           | Implements a (s, S) replenishment policy.                                         |
| [`RQReplenishment`](#rqreplenish)           | Implements a reorder point–quantity (RQ) replenishment policy.                    |
| [`PeriodicReplenishment`](#periodicreplenish)          | Implements periodic review replenishment.                              |
| [`SupplierSelectionPolicy`](#supplierselectionpolicy)  | Abstract base class for supplier selection policies.                   |
| [`SelectFirst`](#selectfirst)               | Selects the first fixed supplier.                                                 |
| [`SelectAvailable`](#selectavailable)       | Selects the first available supplier.                                             |
| [`SelectCheapest`](#selectcheapest)         | Selects the cheapest available supplier.                                          |
| [`SelectFastest`](#selectfastest)           | Selects the fastest available supplier.                                           |
| [`Node`](#nodeclass)                        | Generic node in the supply chain network (e.g., retailer, warehouse, demand).     |
| [`Link`](#linkclass)                        | Transportation or connection link between two nodes in the supply chain.          |
| [`Inventory`](#inventoryclass)              | Inventory maintained by any node, tracking stock levels and related operations.   |
| [`Supplier`](#supplierclass)                | Node representing a supplier of raw materials or products.                        |
| [`InventoryNode`](#inventorynodeclass)      | Node that maintains inventory, such as a warehouse, distributor, or retailer.     |
| [`Manufacturer`](#manufacturerclass)        | Node representing a manufacturer that manufactures a product.                     |
| [`Demand`](#demandclass)                    | Represents demand at a specific node in the network.                              |

---
<!--
## API Reference

### Classes
- [`NamedEntity`](#namedentity)
- [`InfoMixin`](#infomixin)
- [`Statistics`](#statistics)
- [`RawMaterial`](#rawmat)
- [`Product`](#product)
- [`InventoryReplenishment`](#inventoryreplenishment)
    - [`SSReplenishment`](#ssreplenish)
    - [`RQReplenishment`](#rqreplenish)
    - [`PeriodicReplenishment`](#periodicreplenish)
- [`SupplierSelectionPolicy`](#supplierselectionpol)
     - [`SelectFirst`](#selectfirst)
    - [`SelectAvailable`](#selectavailable)
    - [`SelectCheapest`](#selectcheapest)
    - [`SelectFastest`](#selectfastest)
- [`Node`](#node)
- [`Link`](#link)
- [`Inventory`](#inventory)
- [`Supplier`](#supplier)
- [`InventoryNode`](#inventorynode)
- [`Manufacturer`](#manufacturer)
- [`Demand`](#demand)
-->
---

<div id="namedentity"> <h3 class="classhead">Class NamedEntity</h3></div>
:::SupplyNetPy.Components.core.NamedEntity

---

<div id="infomixin">
<h3 class="classhead">Class InfoMixin</h3></div>
:::SupplyNetPy.Components.core.InfoMixin



---

<div id="statistics">
<h3 class="classhead">Class Statistics</h3></div>
:::SupplyNetPy.Components.core.Statistics


---

<div id="rawmat">
<h3 class="classhead">Class RawMaterial</h3></div>
:::SupplyNetPy.Components.core.RawMaterial


---

<div id="product">
<h3 class="classhead">Class Product</h3></div>
:::SupplyNetPy.Components.core.Product


---
<div id="inventoryreplenishment">
<h3 class="classhead">Class InventoryReplenishment</h3></div>
:::SupplyNetPy.Components.core.InventoryReplenishment


---

<div id="ssreplenish">
<h3 class="classhead">Class SSReplenishment</h3></div>
:::SupplyNetPy.Components.core.SSReplenishment


---

<div id="rqreplenish">
<h3 class="classhead">Class RQReplenishment</h3></div>
:::SupplyNetPy.Components.core.RQReplenishment


---
<div id="periodicreplenish">
<h3 class="classhead">Class PeriodicReplenishment</h3></div>
:::SupplyNetPy.Components.core.PeriodicReplenishment


---

<div id="supplierselectionpolicy">
<h3 class="classhead">Class SupplierSelectionPolicy</h3></div>
:::SupplyNetPy.Components.core.SupplierSelectionPolicy


---

<div id="selectfirst">
<h3 class="classhead">Class SelectFirst</h3></div>
:::SupplyNetPy.Components.core.SelectFirst


---

<div id="selectavailable">
<h3 class="classhead">Class SelectAvailable</h3></div>
:::SupplyNetPy.Components.core.SelectAvailable


---
<div id="selectcheapest">
<h3 class="classhead">Class SelectCheapest</h3></div>
:::SupplyNetPy.Components.core.SelectCheapest


---

<div id="selectfastest">
<h3 class="classhead">Class SelectFastest</h3></div>
:::SupplyNetPy.Components.core.SelectFastest


---

<div id="nodeclass">
<h3 class="classhead">Class Node</h3></div>
:::SupplyNetPy.Components.core.Node


---

<div id="linkclass">
<h3 class="classhead">Class Link</h3></div>
:::SupplyNetPy.Components.core.Link


---

<div id="inventoryclass">
<h3 class="classhead">Class Inventory</h3></div>
:::SupplyNetPy.Components.core.Inventory

---

<div id="supplierclass">
<h3 class="classhead">Class Supplier</h3></div>
:::SupplyNetPy.Components.core.Supplier


---
<div id="inventorynodeclass">
<h3 class="classhead">Class InventoryNode</h3></div>
:::SupplyNetPy.Components.core.InventoryNode


---

<div id="manufacturerclass">
<h3 class="classhead">Class Manufacturer</h3></div>
:::SupplyNetPy.Components.core.Manufacturer


---

<div id="demandclass">
<h3 class="classhead">Class Demand</h3></div>
:::SupplyNetPy.Components.core.Demand
