# Replenishment Policies

Imagine a small shop that sells about 30 loaves of bread a day. Again and again, the owner has to decide two things, when to order more bread from the bakery and how many loaves to order. One owner orders whenever the count gets low. Another orders the same amount every Monday. In SupplyNetPy, such a rule is called a replenishment policy. Every distributor, retailer and manufacturer follows one, and you choose it when you create the site.

This guide shows how to choose a built in policy and set it up, and how to write your own policy when none of them fits. The words used here are explained in the [Glossary](../glossary.md).

## Giving a site its policy

A policy is given with two settings. `replenishment_policy` is the policy's class, and `policy_param` is a dictionary with its parameters. Pass the class itself, such as `scm.SSReplenishment`, without creating an object from it. The site creates its policy when the site itself is created.

```python
retailer = {'ID': 'R1', 'name': 'Retailer1', 'node_type': 'retailer',
            'capacity': 300, 'initial_level': 100, 'inventory_holding_cost': 0.2,
            'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s': 80, 'S': 300},
            'product_buy_price': 100, 'product_sell_price': 105}
```

The same two settings work when you create an `InventoryNode` or a `Manufacturer` object yourself.

## The built in policies

The (s, S) and (R, Q) policies decide using the inventory position, the units the site can count on. It is the inventory level, plus the units in transit to the site, minus the units the site still owes to other sites and to waiting customers. The periodic policy orders on a timer instead.

| Policy | When it orders | How many units | Parameters | Class |
|---|---|---|---|---|
| [(s, S) policy](../api-reference/api-ref-core.md#SupplyNetPy.Components.core.SSReplenishment) | The inventory position falls to `s` or below | Enough to bring the inventory position back up to `S` | `s`, `S`, and optionally `safety_stock`, `period`, `first_review_delay` | `SSReplenishment` |
| [(R, Q) policy](../api-reference/api-ref-core.md#SupplyNetPy.Components.core.RQReplenishment) | The inventory position falls to `R` or below | Always `Q` | `R`, `Q`, and optionally `period`, `first_review_delay` | `RQReplenishment` |
| [Periodic policy](../api-reference/api-ref-core.md#SupplyNetPy.Components.core.PeriodicReplenishment) | Every `T` time units | `Q`, plus any units missing from the safety stock | `T`, `Q`, and optionally `safety_stock`, `first_review_delay` | `PeriodicReplenishment` |

Which one to choose depends on how the real site orders.

* The (s, S) policy suits a site that can order any amount and wants each order to fill its inventory up again. The size of each order depends on how much was sold.
* The (R, Q) policy suits a site that orders a fixed amount each time, such as one full truck or one pallet.
* The periodic policy suits a site whose supplier delivers on fixed days, such as once a week. It orders `Q` units every time, whatever the inventory position. If customers buy fewer than `Q` units in `T` time units, the inventory fills up, and later orders are reduced to fit the site's capacity.

Every policy chooses how many units to order, but not from whom. When a site has more than one supplier, its [supplier-selection policy](supplier-selection.md) chooses which one receives each order.

## When a policy checks

By default, the (s, S) and (R, Q) policies check the inventory position each time units leave the site's inventory, so they never miss the moment it reaches the reorder point. Many real sites count their inventory only now and then, for example once a week. To model this, give `period`, and the policy checks only every `period` time units. Between two checks it does nothing, even if the inventory position has fallen below the reorder point.

`first_review_delay` sets how long a policy waits before its first check, or, for the periodic policy, before its first order.

```python
'policy_param': {'s': 80, 'S': 300, 'period': 5, 'first_review_delay': 1}   # checks at 1, 6, 11, 16, ...
```

A policy without a `period` is also woken when the site itself recovers from a disruption. A disruption that destroys units does not wake the policy, so the site checks its inventory position again the moment it is working again. The policy is also woken when one of the site's suppliers, or the link to it, recovers. While every supplier is disrupted, the site cannot place an order, so the policy checks again the moment one recovers, instead of waiting for the next sale. A policy with a `period` keeps to its own timer.

## Safety stock

Safety stock is extra units kept as a buffer against uncertain demand or lead times. The two policies that take a `safety_stock` use it differently.

* The (s, S) policy adds `safety_stock` to both `s` and `S`. So `{'s': 80, 'S': 300, 'safety_stock': 20}` behaves like `{'s': 100, 'S': 320}`.
* The periodic policy looks at the inventory level when it orders. If the level is below `safety_stock`, the order gets the missing units on top of `Q`.

The (R, Q) policy has no safety stock. To keep a buffer with it, raise `R`.

## Mistakes caught when the network is created

A policy ignores any parameter it does not read. So that a typing mistake, or a parameter meant for another policy, does not go unnoticed, a built in policy warns about such a parameter. Passing `T` to the (s, S) policy, for example, gives this warning.

```text
UserWarning: SSReplenishment does not use the parameter(s) 'T' in policy_param, so they are ignored. It uses only 's', 'S', 'safety_stock', 'first_review_delay', 'period'. Check whether you meant to use another replenishment policy.
```

Settings that cannot work stop with an error, for example an `s` larger than `S`, a negative reorder point, or a `Q`, `S` or `T` that is not positive.

## Writing your own policy

When no built in policy fits, write your own as a subclass of `InventoryReplenishment`. Suppose the retailer above orders up to `S` like the (s, S) policy, but its supplier accepts at most 100 units in one order.

```python
class CappedSSReplenishment(scm.InventoryReplenishment):
    _param_keys = ("s", "S", "max_order")

    def run(self):
        s, S = self.params["s"], self.params["S"]
        max_order = self.params["max_order"]
        while True:
            position = self.node.position()
            if position <= s:
                self.node.place_order(min(S - position, max_order))
            yield from self.node.wait_for_drop()
```

Give it to a site like a built in policy.

```python
'replenishment_policy': CappedSSReplenishment,
'policy_param': {'s': 80, 'S': 300, 'max_order': 100},
```

In the policy, `self.node` is the site, `self.params` is its `policy_param`, and `self.env` is the SimPy environment. The `run` method runs for the whole simulation. It loops forever, and in each round it checks, perhaps orders, and then pauses with `yield`, either until the next drop in inventory with `yield from self.node.wait_for_drop()`, or for a fixed time with `yield self.env.timeout(t)`.

The policy works with its site through a small set of helper methods on `Node`, rather than reading or changing the site's internal attributes directly. The built in policies use the same helpers, so a policy written this way does not depend on how `Node` is built inside.

* `node.position()` returns the inventory position. Use it instead of working the position out yourself from `node.inventory.on_hand` and `node.stats.backorder`.
* `node.place_order(quantity)` first checks that some supplier can take the order, then chooses a supplier with the site's supplier-selection policy and places the replenishment order. If every supplier, or the link to it, is disrupted, no order is placed. Use it instead of calling `selection_policy.select(...)` and `env.process(process_order(...))` yourself.
* `node.wait_for_drop()` waits until the site's inventory drops, until the site recovers from a disruption, or until one of its suppliers or the link to it recovers, then gets ready for the next time. A policy that found no supplier to order from is woken this way, so it can check again. Use it as `yield from node.wait_for_drop()`.

To give your policy the warning about unused parameters, list the keys it reads in the class attribute `_param_keys`, as in the example. A policy without such a list is not checked.
