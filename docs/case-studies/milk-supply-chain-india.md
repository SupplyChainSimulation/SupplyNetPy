# Case Study: A National Scale Milk Supply Chain (India)

Milk is one of the most perishable goods distributed at national scale. A packet leaves the processing plant with a shelf life of only a few days, and India, the largest producer of milk in the world, moves it through thousands of distributors and retailers every day. Every facility in that chain faces the same tension. Holding too little stock loses sales, while holding too much means stock expires on the shelf before it sells.

This case study models a national scale milk supply chain for India using SupplyNetPy. The network has three tiers, with 31 manufacturers supplying 282 distributors, which in turn supply 1,498 retailers placed according to census town populations. The study performs an exhaustive evaluation and simulation based optimization to find near optimal replenishment settings, namely the reorder point fraction (alpha) and the order up to fraction (beta), for a given degree of disruption (controlled by the failure rate, p_fail) and a given network structure (controlled by the number of backup distributors per retailer, n_backup).

## Goal of the Study

The goal is to study the combined effect of perishability and disruption on supply chain network performance, measured by profit, service level, and waste. These two forces pull replenishment policy in opposite directions. Perishability punishes excess stock, because units expire before they sell. Disruption punishes lean stock, because a facility that loses its inventory leaves its downstream customers unserved. The experiments quantify this tension and identify the replenishment settings that balance it best at each disruption level, with and without backup distributors.

## The Network

The network is built entirely from public data. Towns are taken from the Census of India 2011, and each town receives a retailer whose demand is proportional to its population. Distributors and manufacturers are placed in larger towns and cities, weighted by state level milk production statistics, and every facility is geocoded to its real coordinates.

Facilities are then connected by nearest neighbor links. Each distributor buys from its nearest manufacturer, and each retailer is linked to its three nearest distributors. One of the three is the primary source and the other two serve as backups. A link is created only when its transport time is shorter than the product shelf life, so milk can never be routed along a path on which it would expire in transit. Lead times and transport costs are derived from road distances. Storage capacities are sized from the daily demand of the population each facility serves. The result is a network of about 3,300 nodes and 6,300 links spanning the country.

The complete network can be explored in the interactive map below. Layers for primary and backup links can be toggled on and off.

<p><a href="../milk-india/supply_chain_map.html" target="_blank"><b>&#128279; Open the interactive supply chain network map</b></a> <small>(opens in a new tab, about 5 MB)</small></p>

## Modeling with SupplyNetPy

The study exercises several capabilities of the library together.

- Perishable inventory with first in, first out expiry, so each batch carries its manufacturing date and is discarded when it ages past the shelf life.
- (s, S) replenishment at every distributor and retailer, with s and S derived from alpha, beta, and the node capacity.
- Supplier selection policies, so a retailer with backup links switches to an available distributor when its primary is disrupted.
- Node disruptions that destroy the stock held at the failed facility, followed by recovery after a downtime.
- Per node statistics that report profit, service, waste, and cost components for every facility in the network.

Each facility is declared as a plain dictionary, and the whole network is just a list of such dictionaries generated programmatically from the data files. A distributor, a retailer with a backup link, and the links between them look like this.

```python
import random
import SupplyNetPy.Components as scm

P_FAIL = 0.005          # daily failure rate, so a failure every 200 days on average

distributor = {'ID': 'D042', 'name': 'Distributor 42', 'node_type': 'distributor',
               'capacity': 11200, 'initial_level': 11200,
               'inventory_type': 'perishable', 'shelf_life': 5,
               'inventory_holding_cost': 0.75,
               'replenishment_policy': scm.SSReplenishment,
               'policy_param': {'s': 1792, 'S': 4480},  # S = beta * capacity, s = alpha * S
               'node_disrupt_time': lambda: random.expovariate(P_FAIL),  # time until the next failure
               'node_recovery_time': lambda: 1.0,  # down for one day
               'disruption_impact': 'destroy_all',  # a failed facility loses all the stock it holds
               'product_buy_price': 20, 'product_sell_price': 24}

retailer = {'ID': 'R0731', 'name': 'Retailer 731', 'node_type': 'retailer',
            'capacity': 1400, 'initial_level': 1400,
            'inventory_type': 'perishable', 'shelf_life': 5,
            'inventory_holding_cost': 0.6,
            'replenishment_policy': scm.SSReplenishment,
            'policy_param': {'s': 224, 'S': 560},
            'supplier_selection_policy': scm.SelectAvailable,  # order from a distributor that is up and has stock
            'supplier_selection_mode': 'dynamic',
            'product_buy_price': 24, 'product_sell_price': 29}

links = [
    {'ID': 'L1', 'source': 'P007', 'sink': 'D042', 'cost': 950.0, 'lead_time': lambda: 0.20},
    {'ID': 'L2', 'source': 'D042', 'sink': 'R0731', 'cost': 120.0, 'lead_time': lambda: 0.05},  # primary
    {'ID': 'L3', 'source': 'D118', 'sink': 'R0731', 'cost': 180.0, 'lead_time': lambda: 0.08},  # backup
]  # costs and lead times come from road distances

net = scm.create_sc_net(nodes=nodes, links=links, demands=demands)
net = scm.simulate_sc_net(net, sim_time=180)
```

## Experiments

The experiments sweep a full factorial grid over the four factors. The replenishment settings alpha and beta, the disruption rate p_fail, and the multihoming level n_backup are varied together, and every configuration is simulated for a 180 day horizon with multiple independent replications. The sweep amounts to roughly 24,000 simulation runs, executed in parallel on an 80 core server. Each run records network profit, customer service level, and waste, with waste separated into stock lost to expiry and stock destroyed by disruptions.

## Insights

Four findings stand out from the sweep.

1. **For perishables, more stock is not safer.** Beyond a modest level, raising the order up to fraction beta reduces both profit and service, because the extra stock expires before it can be sold.
2. **Disruption shifts the optimum.** As failures become more frequent, the best policy holds more stock. The buffer that perishability punishes in calm conditions becomes worth paying for when facilities keep losing their inventory.
3. **Backup distributors pay off.** Every near optimal configuration found by the sweep uses full multihoming. Backup links soften the profit and service loss caused by disruptions at little cost in calm conditions.
4. **A profitable network can hide a struggling tier.** Under heavy disruption the network as a whole remains profitable while the retail tier runs at a loss, a pattern that only becomes visible when performance is examined per node.

The figures below show expected profit as a surface over the alpha and beta grid. The plots are interactive, so they can be rotated, zoomed, and hovered to read individual values. The first surface uses two backups per retailer, and rotating it shows the best (alpha, beta) region moving as disruption grows. The second surface fixes the failure rate at one failure every 200 days on average and shows how profit responds to the replenishment settings at that disruption level.

<iframe src="../milk-india/profit_surface_alpha_beta_nbackup_2.html" width="100%" height="470" style="border:none;" loading="lazy"></iframe>

<iframe src="../milk-india/profit_surface_beta_alpha_pfail_005.html" width="100%" height="470" style="border:none;" loading="lazy"></iframe>

The per node view behind the fourth finding is available as a second interactive map. It shows the measured profit and the expiry waste of every retailer in the country at the best configuration found for each disruption level, with one toggleable layer per disruption level.

<p><a href="../milk-india/retailer_profit_heatmap.html" target="_blank"><b>&#128279; Open the interactive retailer profit and waste map</b></a> <small>(opens in a new tab, about 15 MB)</small></p>

## Status

The study is ongoing. The exhaustive sweep has already produced a large volume of simulation data, and a related research thread builds on it. We are exploring graph neural network (GNN) metamodels for simulation-based optimization of supply chains. A metamodel trained on this data may learn to predict near-optimal values of alpha, beta, and n_backup for a given disruption degree directly from the network, without running thousands of simulations. This page presents a brief introduction to the study and selected insights, and will be updated from time to time as the work matures.
