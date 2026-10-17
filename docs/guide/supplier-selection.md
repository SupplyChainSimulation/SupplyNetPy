# Supplier Selection

Imagine a retailer that can buy the same product from two distributors. Shipping from the first one is cheaper, but its orders take two days to arrive. The second one charges more for transport, and its orders arrive the next day. Each time the retailer orders, it has to pick one of them. In SupplyNetPy, the rule for this choice is called a supplier-selection policy. The replenishment policy decides when to order and how many units, and the supplier-selection policy decides which supplier receives the order.

This guide shows how to choose a built in policy and its mode, how to choose suppliers at random, and how to write your own policy. The words used here are explained in the [Glossary](../glossary.md).

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

In fixed mode the policy's rule decides only the first order and the orders placed during a disruption. So `SelectAvailable` in fixed mode looks at the inventory levels only once. Since fixed is the default of every built in policy except `SelectProbabilistic`, give `supplier_selection_mode='dynamic'` whenever you want the rule applied to every order.

To see where the orders went, print the statistics of the site's links. Each row shows what the site ordered over one link and what arrived.

```python
scm.print_link_wise_performance(sc["nodes"]["R1"].suppliers)
```

## Choosing suppliers at random

Imagine a retailer that spreads its orders over three distributors. About half of its orders go to D1, about 30% to D2 and the rest to D3, with no rule such as the cheapest supplier. Each order goes to one of them by chance, with these shares. `SelectProbabilistic` does this. Give it the probability of each supplier in `supplier_selection_param`, keyed by the ID of the supplier.

```python
retailer = {'ID': 'R1', 'name': 'Retailer1', 'node_type': 'retailer',
            'capacity': 100, 'initial_level': 100, 'inventory_holding_cost': 0.2,
            'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s': 40, 'S': 100},
            'supplier_selection_policy': scm.SelectProbabilistic,
            'supplier_selection_param': {'probabilities': {'D1': 0.5, 'D2': 0.3, 'D3': 0.2}, 'seed': 7},
            'product_buy_price': 100, 'product_sell_price': 110}
```

The probabilities must sum to 1, and none can be negative. A supplier with probability 0 is never chosen. Every link to the site needs a probability, and every probability needs a link, so a mistyped ID is reported when the network is built, before the run. The policy makes a new choice for every order, so it always works in dynamic mode, and `supplier_selection_mode` is not needed.

Over many orders, the shares come close to the probabilities. The statistics of the site's links show the real shares, as above.

### Networks built by a program

A program that builds many networks for an experiment, for example with random links between distributors and retailers, can choose the links and the probabilities in the same loop.

```python
rng = random.Random(1)
distributors = ['D1', 'D2', 'D3', 'D4', 'D5']
links, probabilities = [], {}
for r in ['R1', 'R2']:
    chosen = rng.sample(distributors, k=3)
    weights = [rng.random() for _ in chosen]
    probabilities[r] = {d: w / sum(weights) for d, w in zip(chosen, weights)}
    for d in chosen:
        links.append({'ID': f'{d}{r}', 'source': d, 'sink': r, 'cost': 2, 'lead_time': lambda: 3})
```

Each retailer's dictionary then gets `'supplier_selection_param': {'probabilities': probabilities[r]}`. In a network where every distributor is linked to every retailer, list every distributor, and give 0 to those a retailer should not use.

When you create the objects yourself, a site is created before its links. Give its probabilities once you know them.

```python
r1.selection_policy.set_probabilities({'D1': 0.5, 'D2': 0.3, 'D3': 0.2})
```

The links are checked against them at the site's next order.

### When a supplier is disrupted

The probabilities are the shares while every supplier can take orders. The setting `on_disruption` says what happens when one cannot.

* With `'rescale'` (the default), the order goes to one of the other suppliers, which keep their ratios. With 0.5, 0.3 and 0.2 and D1 disrupted, D2 and D3 get 0.6 and 0.4 for that order. Once D1 recovers, the shares are 0.5, 0.3 and 0.2 again.
* With `'block'`, the choice is made as if no supplier were disrupted. If it falls on a disrupted supplier, the order is not placed, and it is counted as a blocked order at the site and on the link. The site orders again when a supplier or a link recovers, or when its inventory drops.

```python
'supplier_selection_param': {'probabilities': {'D1': 0.5, 'D2': 0.3, 'D3': 0.2}, 'on_disruption': 'block'}
```

If every supplier with a probability above 0 is disrupted, the order is blocked with either setting.

So with disruptions, the shares at the end of a run differ from the probabilities. Say D1 is disrupted during 40% of the orders, and the others never are. With `'rescale'`, D1 receives about 30% of the orders (0.5 × 0.6), and the site never goes without. With `'block'`, D1 is still chosen for half of the orders, but receives only about 37.5% of the orders sent (0.3 out of 0.8), and the site goes without for the blocked orders.

### Random numbers

The policy draws one random number for each order from its own random number generator, so its choices never change any other random numbers in the run, such as those of disruptions. Give a `seed` to repeat the same choices in every run. Two runs with the same seed see the same random numbers, so when you compare two sets of probabilities, only the orders whose number falls near a boundary go to a different supplier. These are common random numbers, explained in [Running Experiments](running-experiments.md). Without a seed, the policy takes one from the site's random number generator, so `scm.set_seed` still makes the run repeatable. You can also give your own `random.Random` as `rng`.

## Manufacturers

A manufacturer does not use a supplier-selection policy. For each raw material, it orders from the first raw-material supplier of that raw material that can take an order, in the order the links were created. While that supplier, or the link to it, is disrupted, it orders from the next one. A manufacturer given a supplier-selection policy, a mode or settings for the policy warns that they are not used.

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

### Policies with settings

A policy can take settings, given to the site in `supplier_selection_param`, just as `SelectProbabilistic` takes its probabilities. Suppose the retailer should order from the cheapest distributor, but skip any distributor that has fewer than 20 units.

```python
class SelectCheapestInStock(scm.SupplierSelectionPolicy):
    _param_keys = ("min_units",)

    def select(self, order_quantity):
        min_units = (self.params or {}).get("min_units", 0)
        candidates = self._active_suppliers()
        stocked = [link for link in candidates if link.available_quantity() >= min_units]
        selected = min(stocked or candidates, key=lambda link: link.cost)
        return self._apply_mode(selected)
```

The site gives the setting with the policy.

```python
'supplier_selection_policy': SelectCheapestInStock, 'supplier_selection_mode': 'dynamic',
'supplier_selection_param': {'min_units': 20},
```

The policy finds its settings in `self.params`. When the site is given no settings, `self.params` is `None`, so the example reads from an empty dict instead and uses 0. When no distributor has 20 units, the policy takes the cheapest one anyway.

`_param_keys` lists the settings the policy reads. The library warns about any other setting, because the policy would ignore it, so a typo such as `'min_unit'` does not go unnoticed. Without `_param_keys`, no setting is checked.

Some settings name suppliers, as the probabilities of `SelectProbabilistic` do. To check them against the site's links, override `check_links(self)` and raise a `ValueError` when a setting does not match. `self.node.suppliers` gives the links, and `link.source.ID` gives the ID of each supplier. `create_sc_net` calls `check_links` once every link exists, so a mistyped supplier ID is reported before the run. If you run a network without `create_sc_net`, call `site.selection_policy.check_links()` yourself once its links are created.
