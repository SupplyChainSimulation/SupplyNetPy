# Supplier Selection

Imagine a retailer that can buy the same product from two distributors. Shipping from the first one is cheaper, but its orders take two days to arrive. The second one charges more for transport, and its orders arrive the next day. Each time the retailer orders, it has to pick one of them. In SupplyNetPy, the rule for this choice is called a supplier-selection policy. The replenishment policy decides when to order and how many units, and the supplier-selection policy decides which supplier receives the order.

This guide shows how to choose a built in policy and its mode, and how to write your own policy. The words used here are explained in the [Glossary](../glossary.md).

## Giving a site its policy

A distributor or retailer that has more than one supplier takes two settings. `supplier_selection_policy` is the policy's class, and `supplier_selection_mode` is `"fixed"` or `"dynamic"`. As with replenishment policies, pass the class itself, without creating an object from it.

```python
retailer = {'ID': 'R1', 'name': 'Retailer1', 'node_type': 'retailer',
            'capacity': 100, 'initial_level': 100, 'inventory_holding_cost': 0.2,
            'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s': 40, 'S': 100},
            'supplier_selection_policy': scm.SelectCheapest, 'supplier_selection_mode': 'dynamic',
            'product_buy_price': 100, 'product_sell_price': 110}
```

Without these settings, a site uses `SelectFirst` in fixed mode, so it orders from the supplier whose link was created first. A site with only one supplier does not need them.

## The built in policies

Each policy chooses among the suppliers that can take an order right now. A supplier is skipped while its site, or the link to it, is disrupted.

| Policy | Chooses | Class |
|---|---|---|
| [First](../api-reference/api-ref-core.md#SupplyNetPy.Components.core.SelectFirst) | The supplier whose link was created first | `SelectFirst` |
| [Available](../api-reference/api-ref-core.md#SupplyNetPy.Components.core.SelectAvailable) | The first supplier whose inventory level can fill the whole order. If none can, the first supplier, and the order waits there until enough units arrive | `SelectAvailable` |
| [Cheapest](../api-reference/api-ref-core.md#SupplyNetPy.Components.core.SelectCheapest) | The supplier with the lowest transportation cost, the `cost` of the link to it | `SelectCheapest` |
| [Fastest](../api-reference/api-ref-core.md#SupplyNetPy.Components.core.SelectFastest) | The supplier with the shortest lead time | `SelectFastest` |

When lead times are random, `SelectFastest` draws one lead time from each link to compare them. The shipment then draws its own lead time, so the chosen supplier is the one that looked fastest at that moment, and it may still turn out slower.

## Fixed or dynamic

The mode says how often the choice is made.

* In **dynamic** mode, the policy chooses again for every replenishment order. Use it when the best supplier can change during a run, for example with `SelectAvailable`, whose answer depends on the inventory levels at that moment, or with `SelectFastest` and random lead times.
* In **fixed** mode, the policy keeps the first supplier it chose and sends every later order there. This models a site with a regular supplier. While that supplier, or the link to it, is disrupted, the orders go to another supplier, chosen by the same rule. Once it recovers, the orders go back to it.

In fixed mode the policy's rule decides only the first order and the orders placed during a disruption. So `SelectAvailable` in fixed mode looks at the inventory levels only once. Since fixed is the default, give `supplier_selection_mode='dynamic'` whenever you want the rule applied to every order.

To see where the orders went, print the statistics of the site's links. Each row shows what the site ordered over one link and what arrived.

```python
scm.print_link_wise_performance(sc["nodes"]["R1"].suppliers)
```

## Manufacturers

A manufacturer does not use a supplier-selection policy. For each raw material, it orders from the first raw-material supplier of that raw material that can take an order, in the order the links were created. While that supplier, or the link to it, is disrupted, it orders from the next one.

## Writing your own policy

When no built in policy fits, write your own as a subclass of `SupplierSelectionPolicy`. Suppose the retailer above should order from whichever distributor has the most units right now.

```python
class SelectMostStock(scm.SupplierSelectionPolicy):
    def select(self, order_quantity):
        candidates = self._active_suppliers()
        selected = max(candidates, key=lambda link: link.available_quantity())
        return self._apply_mode(selected)
```

Give it to a site like a built in policy.

```python
'supplier_selection_policy': SelectMostStock, 'supplier_selection_mode': 'dynamic',
```

A site reaches each supplier over a link, so the policy works with links. `select` is called with the number of units in the order and returns the link to the chosen supplier. Follow the same three steps as the built in policies.

1. `self._active_suppliers()` returns the links in `self.node.suppliers` that can take an order right now, so disrupted suppliers and links are skipped.
2. Choose one of them with your own rule.
3. `return self._apply_mode(selected)` applies the fixed or dynamic mode, so your policy follows `supplier_selection_mode` like the built in ones.

To compare suppliers, use what the link offers. `link.available_quantity()` gives the supplier's inventory level, so the policy does not need to reach past the link into the supplier's inventory. `link.cost` is the transportation cost, `link.lead_time()` draws a lead time, and `link.source` is the supplier itself.
