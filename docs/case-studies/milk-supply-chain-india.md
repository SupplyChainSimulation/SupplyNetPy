# A National Scale Milk Supply Chain (India)

Milk is one of the perishable goods distributed at national scale. A packet leaves the processing plant with a shelf life of only a few days, and India, the largest producer of milk in the world, moves it through thousands of distributors and retailers every day. Every site in that chain faces the same tension. Holding too few units loses sales, while holding too many means units expire before they sell. On top of that, a distributor can be disrupted, for example by a power cut that stops its cold storage, and then all the milk it holds is lost.

This case study models a national scale milk supply chain for India using SupplyNetPy. The network has three levels, with 31 manufacturers supplying 282 distributors, which in turn supply 1,498 retailers placed according to census town populations. The study tries every combination of two replenishment settings, the reorder point fraction (alpha) and the order up to fraction (beta), for six levels of disruption (set by the disruption probability, p_fail) and for zero, one or two backup distributors per retailer (n_backup). It then finds the settings that earn the most profit in each case.

## Goal of the Study

The study asks three questions. How much do disruptions at distributors cost the chain? How much of that cost do backup distributors win back? Which replenishment settings earn the most, and do they change when disruptions become more frequent? Perishability and disruption seem to pull the replenishment policy in opposite directions. Perishability punishes holding too many units, because they expire before they sell. Disruption seems to punish holding too few, because a site that loses its inventory leaves its customers unserved. The experiments measure how these forces play out across the whole network, with profit, service level (the share of customer demand that is fulfilled), and waste as the measures.

## The Network

The network is built entirely from public data. Towns are taken from the Census of India 2011, and each town that receives a retailer gets demand in proportion to its population. The number of manufacturers in each state follows the state's milk production, taken from the Basic Animal Husbandry Statistics 2020 of the Department of Animal Husbandry and Dairying. Distributors are shared among the states by urban population, and retailers are drawn across the whole country with larger towns more likely to be chosen. Every site sits at the real coordinates of its town, found with the OpenStreetMap geocoding service. The result has manufacturers in 16 states, distributors in 27 states, and retailers in 31 states and union territories.

Sites are then connected to their nearest neighbors. Each distributor buys from its nearest manufacturer, and each retailer is linked to its three nearest distributors. The nearest one is its primary distributor and the other two are its backups. Lead times and transportation costs come from the distance between the two sites. The lead time in days is the distance in km divided by 480, the distance a truck moving at 20 km per hour covers in a day, and each shipment costs 10 rupees per km. A distributor is linked to a manufacturer only when the lead time is shorter than the shelf life, so milk is never sent along a link on which it would expire in transit. On average a retailer is 48 km from its primary distributor and a distributor is 150 km from its manufacturer.

The capacity of a site is four days of the demand it serves, assuming that one person in five buys one 500 mL packet a day. A retailer cannot hold more than its capacity. A distributor has no storage limit, so only its replenishment policy limits how much it holds. The whole network has 3,309 nodes (1,811 sites and 1,498 customer demands) and 6,274 links spanning the country.

The complete network can be explored in the interactive map below. Layers for primary and backup links can be toggled on and off.

<p><a href="../milk-india/supply_chain_map.html" target="_blank"><b>&#128279; Open the interactive supply chain network map</b></a> <small>(opens in a new tab, about 5 MB)</small></p>

## Modeling with SupplyNetPy

The study uses several capabilities of the library together.

* Perishable inventory, with the oldest units sold first. Each batch carries its manufacturing date and is thrown away when it passes its shelf life of five days. The date is set to the moment the distributor orders the milk, so the five days cover the lead time and the time spent at both the distributor and the retailer.
* An (s, S) policy at every distributor and retailer, which orders back up to the order-up-to level S whenever the inventory position (units at the site and in transit, minus backorders) falls to the reorder point s. The two levels come from beta and alpha, with S equal to beta times the capacity of the site and s equal to alpha times S.
* Supplier-selection policies. A retailer with backup links uses `SelectAvailable`, which picks its primary distributor if it is working and holds enough units, and otherwise the first backup that does.
* Disruptions at distributors. The time to the next disruption is drawn at random, with an average of 1/p_fail days. A disruption lasts one day and destroys every unit at the distributor (`disruption_impact="destroy_all"`). When it recovers, the distributor starts with no inventory and orders from its manufacturer straight away.
* Customer demand at every retailer, with orders of about 500 packets arriving at random times. A customer takes whatever the retailer has, and the rest of the order becomes lost sales.
* A warm-up. Every run starts with each site full of fresh milk, which is more than any policy holds later and would all expire on the same day. The statistics are therefore reset after 20 days with `scm.reset_stats`, and the run carries on.
* Statistics for each node that report profit, service, waste, and costs for every site in the network.

Each site is described by a plain dictionary, and the whole network is just a list of such dictionaries, created by a program from the data files. A manufacturer, a distributor, a retailer with a backup link, its customers, and the links between them look like this.

```python
import random
import SupplyNetPy.Components as scm

P_FAIL = 1/100          # chance a disruption starts each day (one every 100 days on average)
ALPHA, BETA = 0.5, 0.2  # reorder point fraction and order up to fraction

manufacturer = {'ID': 'M07', 'name': 'Manufacturer 7', 'node_type': 'warehouse',
                'capacity': float('inf'), 'initial_level': 1e12,  # never runs out of milk
                'inventory_holding_cost': 0.0,
                'replenishment_policy': scm.SSReplenishment,
                'policy_param': {'s': 1, 'S': 1e12},
                'product_buy_price': 20, 'product_sell_price': 20}

cap_d = 11200           # four days of the demand the distributor serves
distributor = {'ID': 'D042', 'name': 'Distributor 42', 'node_type': 'distributor',
               'capacity': float('inf'), 'initial_level': cap_d,  # no storage limit
               'inventory_type': 'perishable', 'shelf_life': 5,
               'manufacture_date': lambda now: now - 0.3,  # dated when ordered, 0.3 days ago
               'inventory_holding_cost': 0.75,
               'replenishment_policy': scm.SSReplenishment,
               'policy_param': {'s': ALPHA * BETA * cap_d, 'S': BETA * cap_d},
               'node_disrupt_time': lambda: random.expovariate(P_FAIL),  # time until the next disruption
               'node_recovery_time': lambda: 1.0,  # each disruption lasts one day
               'disruption_impact': 'destroy_all',  # a disrupted site loses all its units
               'product_buy_price': 20, 'product_sell_price': 24}

cap_r = 5600            # four days of the retailer's own demand
retailer = {'ID': 'R0731', 'name': 'Retailer 731', 'node_type': 'retailer',
            'capacity': cap_r, 'initial_level': cap_r,
            'inventory_type': 'perishable', 'shelf_life': 5,
            'inventory_holding_cost': 0.6,
            'replenishment_policy': scm.SSReplenishment,
            'policy_param': {'s': ALPHA * BETA * cap_r, 'S': BETA * cap_r},
            'supplier_selection_policy': scm.SelectAvailable,  # a distributor that is not disrupted and has enough units
            'supplier_selection_mode': 'dynamic',
            'product_buy_price': 24, 'product_sell_price': 29}

customers = {'ID': 'C0731', 'name': 'Customers of R0731', 'node_type': 'demand',
             'demand_node': 'R0731',
             'order_arrival_model': lambda: random.expovariate(1400 / 500),  # 1,400 packets a day, in orders of about 500
             'order_quantity_model': lambda: max(1, round(random.gauss(500, 150))),
             'consume_available': True}  # take what is there, the rest is lost sales

links = [
    {'ID': 'L1', 'source': 'M07', 'sink': 'D042', 'cost': 1440.0, 'lead_time': lambda: 0.3},
    {'ID': 'L2', 'source': 'D042', 'sink': 'R0731', 'cost': 120.0, 'lead_time': lambda: 0.025},  # primary
    {'ID': 'L3', 'source': 'D118', 'sink': 'R0731', 'cost': 180.0, 'lead_time': lambda: 0.0375},  # backup
]  # costs and lead times come from the distance between the sites

nodes = [manufacturer, distributor, retailer]  # and the other 1,808 sites, built the same way
demands = [customers]                          # and the other 1,497 customer demands
net = scm.create_sc_net(nodes=nodes, links=links, demands=demands)
net = scm.simulate_sc_net(net, sim_time=20)    # warm-up
scm.reset_stats(net)                           # start counting again
net = scm.simulate_sc_net(net, sim_time=180)   # the 160 measured days
```

## Experiments

The experiments sweep a full grid over the four factors. Alpha and beta each take the ten values 0.1, 0.2, and so on up to 1.0. The disruption probability takes six values, from no disruptions through one disruption every 200, 150, 100, and 50 days, up to one every 25 days at each distributor. The number of backup distributors is 0, 1, or 2. That makes 1,800 configurations, and each one is run 10 times with different random numbers (10 replications), for 18,000 runs in all. Each run lasts 180 days, and the first 20 days are left out as a warm-up.

Replication number r of every configuration uses the same random numbers, so all 1,800 configurations face exactly the same customers. Two configurations can then be compared run by run, which makes even small differences reliable. The runs were spread over 76 worker processes on an 80 core server. A typical run took about half an hour, and the whole grid took 7.5 days.

Profit is the sum of the profits of all distributors and retailers, per day. The payments of retailers to distributors cancel out in this sum, so the milk is paid for once, when a distributor buys it at 20 rupees a packet. A packet that expires or is destroyed therefore costs the chain its price. Each run also records the service level, the lost sales, and two kinds of waste, expired units and units destroyed in disruptions.

## Insights

Two configurations frame the results. The baseline, with alpha 0.4 and beta 0.5, orders up to two days of demand at every site. The best configuration found by the sweep, with alpha 0.5 and beta 0.2, orders up to only 0.8 days of demand. The table gives profit (in million rupees a day) and service level for both, with no backup and with one backup distributor. Each value is the average of 10 replications.

| Disruptions | Baseline, no backup | | Baseline, 1 backup | | Best, no backup | | Best, 1 backup | |
|---|---|---|---|---|---|---|---|---|
| | profit | service | profit | service | profit | service | profit | service |
| none | 176.0 | 0.9999 | 175.8 | 0.9999 | 205.8 | 0.9923 | 205.7 | 0.9911 |
| 1 in 200 days | 172.9 | 0.9992 | 172.9 | 0.9999 | 204.2 | 0.9892 | 204.8 | 0.9907 |
| 1 in 150 days | 171.7 | 0.9990 | 171.9 | 0.9999 | 203.6 | 0.9881 | 204.4 | 0.9907 |
| 1 in 100 days | 169.6 | 0.9985 | 169.8 | 0.9999 | 202.4 | 0.9858 | 203.7 | 0.9902 |
| 1 in 50 days | 162.8 | 0.9970 | 163.6 | 0.9998 | 199.2 | 0.9793 | 201.7 | 0.9894 |
| 1 in 25 days | 150.5 | 0.9943 | 152.5 | 0.9997 | 193.0 | 0.9674 | 198.1 | 0.9877 |

Six findings stand out from the sweep.

1. **Each disruption costs about the same, and that cost is mostly destroyed milk.** The loss per disruption hardly changes with how often disruptions happen, and almost all of it is the milk destroyed at the distributor. Customers barely notice, even without backups.
2. **Holding less inventory earns more and makes disruptions cheaper.** The best configuration keeps far less milk at distributors, so it earns more and loses less in each disruption, at every disruption level. Extra inventory does not protect against disruptions, because it sits at the very site that gets disrupted. The price is a slightly lower service level.
3. **Backup distributors win back lost sales, not destroyed milk.** A backup lets a retailer keep ordering while its distributor is disrupted, but it cannot save the milk that distributor loses. Backups therefore help most when inventory is lean, so inventory policy and backups should be chosen together.
4. **One backup is enough.** The first backup pays off more and more as disruptions become frequent, while a second one adds almost nothing. The results also show the most a backup link could cost and still pay for itself.
5. **A service target makes backups far more valuable.** Without backups, meeting a high service target under frequent disruptions needs much more inventory and costs a large share of the profit. With one backup, a lean configuration close to the best one meets the same target at little cost.
6. **Expiry stays small until the inventory in the chain nears the shelf life.** Little milk expires while sites hold modest inventory, but expiry climbs steeply once the inventory along the chain approaches the five day shelf life. Disruptions do not increase expiry.

The figures below show expected profit as a surface over the alpha and beta grid. The plots are interactive, so they can be rotated, zoomed, and hovered to read individual values. They give profit in crore rupees a day, where one crore is ten million. The first surface uses two backups per retailer and has one layer per disruption level. Switching between the layers shows the whole surface sinking as disruptions grow, while its peak stays at the same alpha and beta. The second surface fixes the disruption probability at one disruption every 150 days and compares zero, one, and two backups.

<iframe src="../milk-india/profit_surface_alpha_beta_nbackup_2.html" width="100%" height="560" scrolling="no" style="border:none;" loading="lazy"></iframe>

<iframe src="../milk-india/profit_surface_beta_alpha_pfail_1over150.html" width="100%" height="560" scrolling="no" style="border:none;" loading="lazy"></iframe>

The network totals hide large differences between retailers. Even at the best configuration, a small group of retailers accounts for most of the lost sales. Most of them are far from their manufacturer, so their reorder point is shorter than their lead time, while retailers in small towns keep so few units that a handful of customer orders empties them. A reorder point that grows with the lead time of each site is a natural next step.

The second interactive map shows this per retailer view. It gives the profit and the expiry waste of every retailer in the country at the best configuration for each disruption level, with one layer per disruption level. Clicking a retailer shows its profit and service level at every disruption level.

<p><a href="../milk-india/retailer_profit_heatmap.html" target="_blank"><b>&#128279; Open the interactive retailer profit and waste map</b></a> <small>(opens in a new tab, about 35 MB)</small></p>

## Further work

The study points to several open questions. Since only distributor inventory is destroyed in a disruption, holding a larger share of the inventory at retailers may protect sales without adding to the destroyed milk, but the milk then ages at the retailer. Backup links could be given a cost and chosen retailer by retailer. Disruptions that hit a region at once, and disruptions that last longer than a day, would test backups harder.

The exhaustive sweep also produced a large volume of simulation data, and a related research thread builds on it. We are exploring graph neural network (GNN) metamodels for simulation based optimization of supply chains. A metamodel trained on this data may learn to predict near optimal values of alpha, beta, and n_backup for a given disruption degree directly from the network, without running thousands of simulations.
