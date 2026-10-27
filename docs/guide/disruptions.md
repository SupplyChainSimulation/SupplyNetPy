# Disruptions

Imagine a distributor whose warehouse is flooded for a week. While the water is there, its retailers cannot order from it, and the customers who come to its door are turned away. The trucks already on the road still arrive, and once the water is gone, the distributor works as before. Some of the units inside may be ruined. In SupplyNetPy, such an event is called a disruption, and it can hit a site or a link.

This guide shows how to make sites and links disrupted, at fixed times or at random, what happens to orders while they are, how the disruptions show up in the statistics, and how to model units lost in a disruption. The words used here are explained in the [Glossary](../glossary.md).

## What a disruption does

A disrupted site takes no new orders, neither replenishment orders from its buyers nor orders from customers. A disrupted link carries no new orders. Everything else goes on as before.

* Orders the site took before the disruption are still served, and customers who were already waiting keep waiting and are served.
* Shipments in transit still arrive, even over a disrupted link. See [Known Issues](../known-issues.md).
* The site itself still places its own replenishment orders and receives deliveries. A raw-material supplier still mines, and a manufacturer still makes its product.
* The units at the site are left alone, unless you set a disruption impact, described at the end of this guide.

## Scheduled and random disruptions

Sites and links take the same three settings, with slightly different names.

| What it sets | Site | Link |
|---|---|---|
| Time units until the next disruption, for scheduled disruptions | `node_disrupt_time` | `link_disrupt_time` |
| Disruption probability, the chance each time unit that a disruption starts | `failure_p` | `link_failure_p` |
| Time units a disruption lasts, 1 if not given | `node_recovery_time` | `link_recovery_time` |

Each of them can be a number or a function with no arguments that returns one, so every disruption can be different.

A **scheduled** disruption starts after `node_disrupt_time` time units, counted from the start of the run and then from each recovery. So the settings below disrupt the site from 30 to 35, from 65 to 70, and so on.

```python
'node_disrupt_time': 30, 'node_recovery_time': 5
```

A **random** disruption can start in any time unit, with the chance `failure_p`. The settings below give a link a 2% chance each time unit of a disruption that lasts between 1 and 4 time units.

```python
'link_failure_p': 0.02, 'link_recovery_time': lambda: random.uniform(1, 4)
```

If both are given, the scheduled disruption is used and `failure_p` is ignored. Remember to give a recovery time. Without it, every disruption lasts only 1 time unit.

Random disruptions draw random numbers, so two runs give different results. To repeat exactly the same run, call `scm.set_seed(n)` once before you build the network.

## What happens to orders

* **Replenishment orders.** When a buyer orders, its [supplier-selection policy](supplier-selection.md) skips every supplier whose site or link is disrupted. If no supplier can take the order, the order is not placed. It is counted in the buyer's `blocked` statistic, and the buyer's [replenishment policy](replenishment-policies.md) checks again as soon as a supplier or a link recovers.
* **Manufacturers.** A manufacturer plans production only when it can order every raw material. If every raw-material supplier of even one raw material is disrupted, it plans nothing until one recovers.
* **Customers.** A customer who arrives at a disrupted site is turned away. The order is counted in the site's `disruption_lost_sales`, and not in its shortage, because the site did not run out of units. It could not take the order.

## Disruptions in the statistics

The statistics of every site, and of every link in `link.stats`, record its disruptions.

| Statistic | Meaning |
|---|---|
| `disruptions` | How many disruptions started |
| `disrupted_time` | How many time units the site or link was disrupted in all |
| `availability` | The share of time it was not disrupted |
| `blocked` | Replenishment orders a buyer could not place because every supplier, or the link to it, was disrupted. Recorded at the buyer |
| `disruption_lost_sales` | Customer orders a site lost because it was disrupted when they arrived |

A retailer disrupted from 30 to 35 and from 65 to 70 in a run of 100 time units has `disruptions` 2, `disrupted_time` 10 and `availability` 0.9.

## What a disruption does to stored inventory

A disruption in the real world can take many forms, such as a natural disaster, a power cut, contamination, theft or a strike, and each affects the units at a site differently. The settings above only mark the site as disrupted. They do *not* describe what happens to the units already there.

If you want the simulation to also account for units that are physically lost in a disruption, set the `disruption_impact` argument when you create the site (and, if you choose `"destroy_fraction"`, also `disruption_loss_fraction`). The available choices are listed below.

| `disruption_impact` value | What happens the moment a disruption starts |
| --- | --- |
| `None` (the default) or `"none"` | The site is disrupted, but its units are left alone. |
| `"destroy_all"` | All units at the site are lost. For a `Manufacturer`, its raw materials are lost too, since the idea behind this choice is that every physical thing at the site is gone. Infinite suppliers (which never run out) are skipped, since destroying an unlimited supply has no meaning. |
| `"destroy_fraction"` | A share of the inventory level is lost. The share is given by `disruption_loss_fraction`, which can be a fixed number between 0 and 1 (for example `0.3` to lose 30%) or a small function that returns a different number each time, if you want random losses. |
| A function `f(node)` | For anything more specific. You write a short Python function describing the effect, and the simulator calls it with the site when a disruption starts. For example, a contamination that destroys only certain batches, damage that reduces capacity, or a lead time penalty that applies once the site recovers. |

The effect is applied **once**, exactly at the moment the site goes from active to inactive, both for scheduled and random disruptions. It is *not* applied again while the site stays disrupted. If you want a loss that grows over time during a disruption (slow spoilage from a long loss of cooling, ongoing theft), write that inside your own function, where you can start your own SimPy process and time it against `node_recovery_time`.

The two built in choices call `Inventory.destroy(amount, reason)`, a public method on `Inventory` that removes the units at once, even when orders are waiting at the site. For perishable products, the oldest batches are destroyed first. One subtle but important detail is that `destroy` does **not** wake up the replenishment policy, because a site should not place replenishment orders while it is disrupted. Instead, the site wakes its replenishment policy when it recovers. The policy then checks the inventory position and orders if it is too low, so a site that lost all its units refills its inventory as soon as it is working again. Note that a disrupted site can still order in two cases. A replenishment policy with a `period` orders when its time comes, and a policy is woken when one of the site's suppliers, or the link to it, recovers during the site's disruption. `destroy` also wakes a raw-material supplier, which then mines again to refill its inventory, and a manufacturer, which can then make more. If you write your own impact function that destroys units, call `Inventory.destroy(...)` for the same reasons, and do not change `level`, `on_hand` or `perish_queue` by hand.

The units destroyed (`destroyed_qty`) and their value (`destroyed_value`) are recorded in the site's statistics. `destroyed_value` is one of the site's costs, so it is automatically included in `node_cost` and therefore in `profit`, and you do not need to subtract it yourself. In your own impact function, report losses the same way, with `node.stats.update_stats(destroyed_qty=qty, destroyed_value=qty * unit_cost)`, rather than inventing separate statistics that the simulator will not know about.

A short example.

```python
import random
import SupplyNetPy.Components as scm

# Destroy all units when a disruption starts, as in a natural disaster.
distributor = scm.InventoryNode(
    env=env, ID="D1", name="D1", node_type="warehouse",
    capacity=200, initial_level=120, inventory_holding_cost=0.2,
    replenishment_policy=scm.SSReplenishment, policy_param={'s': 100, 'S': 200},
    product_sell_price=10, product_buy_price=5,
    node_disrupt_time=lambda: 30, node_recovery_time=lambda: 5,
    disruption_impact="destroy_all",
)

# Like a power cut, each disruption destroys between 10% and 40% of the inventory level.
warehouse = scm.InventoryNode(
    ..., disruption_impact="destroy_fraction",
    disruption_loss_fraction=lambda: random.uniform(0.1, 0.4),
)
```
