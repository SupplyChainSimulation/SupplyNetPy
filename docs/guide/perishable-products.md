# Perishable Products

Imagine a dairy that makes milk which can be sold for 5 days after it is made. A distributor buys the milk and sends it on to retailers, 2 days away. By the time a packet reaches a retailer, it has only 3 days left, and whatever is not sold by then is thrown away. Holding too few packets loses sales, while holding too many means packets expire before they sell. In SupplyNetPy, such a product is perishable, and every site that holds it keeps track of when its units were made.

This guide shows how to make a product perishable, how batches and their manufacturing dates move through the supply chain, when units expire, and how expired units show up in the statistics. The words used here are explained in the [Glossary](../glossary.md).

## Making a product perishable

Give each site that holds the product `inventory_type="perishable"` and a `shelf_life`, the time units a unit can be sold after it is made.

```python
retailer = {'ID': 'R1', 'name': 'Retailer 1', 'node_type': 'retailer',
            'capacity': 100, 'initial_level': 60, 'inventory_holding_cost': 0.1,
            'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s': 20, 'S': 60},
            'product_buy_price': 1, 'product_sell_price': 3,
            'inventory_type': 'perishable', 'shelf_life': 5}
```

Distributors, retailers and other inventory sites (_InventoryNode_) and manufacturers (_Manufacturer_) can hold a perishable product. SupplyNetPy does not model perishable raw materials yet, so the inventory of a raw-material supplier and the raw materials a manufacturer holds are always non-perishable. A site without these settings keeps its units forever, even when its supplier's units are perishable.

## Batches and manufacturing dates

A perishable inventory keeps its units as batches, units with the same manufacturing date. A unit expires `shelf_life` time units after its manufacturing date. Where the date comes from depends on how the units arrive.

| Units | Manufacturing date |
|---|---|
| The initial units of a site | Time 0 |
| Units a manufacturer makes | The time their production batch is finished |
| Units from a supplier whose product is perishable | The date they already have, so they keep it from site to site |
| Units from a supplier whose product is not perishable, such as an infinite supplier | The time they arrive, or `manufacture_date(t)` if you give it |

`manufacture_date` is a function that takes the arrival time and returns a manufacturing date. It describes units that were made before they reached the site. For example, `lambda t: t - 1` dates every delivery 1 time unit before it arrives.

## Oldest units first

Every order takes units from the oldest batch first, then from the next oldest, and so on. This holds for customer orders and for replenishment orders from other sites. The batches go with the units to the buyer.

Say a retailer has 10 units made at time 0 and 20 units made at time 3. A customer who orders 15 units gets the 10 from time 0 and 5 from time 3, and the retailer keeps 15 units made at time 3.

## When units expire

The moment a batch reaches the end of its shelf life, its units are thrown away, even if orders are waiting at the site. The inventory level drops, so the site's [replenishment policy](replenishment-policies.md) checks at once whether to order.

A unit's shelf life is counted from its manufacturing date, not from its arrival, so the lead time uses up part of it. In the dairy above, milk made at time 0 that reaches a retailer at time 2 expires there at time 5. Units do not expire while they are in transit. Units whose shelf life ends on the way are thrown away when they arrive, after the buyer has paid for them, so if a lead time is as long as the shelf life, every unit arrives already expired. So keep every lead time shorter than the shelf life.

Each site uses its own `shelf_life` with the date the units carry. A retailer with a shelf life of 10 that buys units made at time 0 from a distributor with a shelf life of 5 keeps them until time 10. Give every site that holds the same product the same shelf life, unless the sites really do keep it differently, for example one with cooling and one without.

## Expired units in the statistics

A site's expired units are counted in `inventory_waste`, and `simulate_sc_net` adds them up for the whole network in `sc["inventory_waste"]`. A warm-up resets the count, as described in the [Statistics and Results](statistics.md) guide.

SupplyNetPy does not give expired units a price of their own. The site paid for them when they arrived, which is in `inventory_spend_cost`, it was charged the holding cost until they expired, and they bring in no revenue, so they already lower its profit. If your study gives waste a cost of its own, multiply `inventory_waste` by that cost.

## Choosing the replenishment settings

A replenishment policy looks at the inventory position, and counts units that are about to expire the same as fresh ones. For a perishable product, holding more is not always safer. Once a site holds more than it sells within the shelf life, every extra unit expires, so a higher `S` or a larger safety stock can lower both the profit and the share of customers served. Compare a few settings by running them, as in the [Milk Supply Chain (India)](../case-studies/milk-supply-chain-india.md) case study. The [Pharmacy Supply Chain](../case_study_pharma.md) case study is another worked example with a perishable product.
