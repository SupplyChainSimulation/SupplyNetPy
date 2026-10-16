# Running Experiments

Imagine a shop manager who wants to know whether to reorder when 60 units are left or when 120 are left. One simulated year gives an answer, but customers arrive at random, so another year could give a different one. To answer the question properly, the manager simulates many years with each setting, compares the averages, and checks how precise they are. Each of these runs is a replication.

This guide shows how to set up a network so that it can be run many times, how to control its random numbers with seeds, how to compare settings fairly, and how to collect and summarize the results. The words used here are explained in the [Glossary](../glossary.md).

## A function that builds the network

A network can be simulated only once from the start. Calling `simulate_sc_net` again with the same `sim_time` simulates nothing more and gives a warning. So write a function that builds a fresh network, and call it for every run. Its arguments are the settings you want to vary and the seed of the run.

```python
import random
import statistics
import SupplyNetPy.Components as scm

def build(s, seed):
    demand_rng = random.Random(f"demand {seed}")       # random numbers of the customers
    lead_rng = random.Random(f"lead time {seed}")      # random numbers of the lead times
    nodes = [{'ID': 'S1', 'name': 'Supplier', 'node_type': 'infinite_supplier'},
             {'ID': 'R1', 'name': 'Shop', 'node_type': 'retailer',
              'capacity': 300, 'initial_level': 150, 'inventory_holding_cost': 0.2,
              'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s': s, 'S': 300},
              'product_buy_price': 4, 'product_sell_price': 10}]
    links = [{'ID': 'L1', 'source': 'S1', 'sink': 'R1', 'cost': 20,
              'lead_time': lambda: lead_rng.randint(1, 3)}]
    demands = [{'ID': 'd1', 'name': 'Customers', 'demand_node': 'R1',
                'order_arrival_model': lambda: demand_rng.expovariate(1),
                'order_quantity_model': lambda: demand_rng.randint(5, 15)}]
    return scm.create_sc_net(nodes, links, demands)

def run(s, seed):
    sc = build(s, seed)
    scm.simulate_sc_net(sc, sim_time=365, logging=False)
    return sc
```

Pass `logging=False` to `simulate_sc_net`. With logging on, every run prints its whole log and writes it to a file, which slows down a study of many runs and buries its output.

## Seeds

Each run above draws its random numbers from its own random number generators, started from the seed. The same seed gives the same customers and the same lead times, so `run(60, 1)` gives the same profit every time it is called, and a result can always be repeated.

The seeds here are strings such as `"demand 1"`, so the customers and the lead times of one run get different random numbers, and no run reuses the numbers of another.

If the network has random disruptions, also call `scm.set_seed(seed)` before you build it. It seeds the random numbers the library itself uses for disruptions.

## Comparing settings fairly

Run every setting with the same seeds. Then each setting faces exactly the same customers and lead times, and the differences in the results come from the settings themselves. This is called common random numbers.

That is why the customers and the lead times have separate generators. If they shared one, the lead times of the replenishment orders would use up random numbers in a different order under each setting, and from then on the two settings would see different customers.

```python
rows = []
for s in (60, 120):
    for seed in range(30):
        sc = run(s, seed)
        shop = sc["nodes"]["R1"].stats
        rows.append({'s': s, 'seed': seed, 'profit': sc["profit"],
                     'lost_sales': shop.lost_sales[1],
                     'avg_inventory_level': shop.avg_inventory_level})
```

Each row holds the settings, the seed and the results you want to keep, from the network results (`sc["profit"]`) or from the statistics of a node. The [Statistics and Results](statistics.md) guide lists what there is.

## Averages and confidence intervals

The average over the replications is the estimate, and its confidence interval shows how precise it is.

```python
for s in (60, 120):
    profits = [row['profit'] for row in rows if row['s'] == s]
    mean = statistics.mean(profits)
    half_width = 1.96 * statistics.stdev(profits) / len(profits) ** 0.5
    print(f"s = {s}: profit {mean:.0f} ± {half_width:.0f}")
```

This prints a profit of 10161 ± 651 for `s` 60 and 7696 ± 581 for `s` 120, as 95% confidence intervals. To narrow an interval, run more replications. Four times as many make it about half as wide.

Because both settings used the same seeds, the difference can also be measured run by run. The profit with `s` 60 minus the profit with `s` 120, for the same seed, averages 2465 ± 159. That interval is much narrower than the two above, because the luck of each run, a busy year or a quiet one, is the same for both settings and cancels out.

With pandas installed, `pandas.DataFrame(rows)` turns the rows into a table, and `df.groupby('s')['profit'].agg(['mean', 'std'])` gives the same averages.

## Run length and warm-up

`sim_time` is the time at which the run stops, and events due at exactly that time do not happen. So `sim_time=365` covers time 0 up to just before 365.

Every run starts with its initial inventory levels, nothing in transit and no orders waiting. To leave this first stretch out of the results, run a warm-up before the measured period.

```python
sc = build(60, 1)
net = scm.Network(sc)
net.simulate(30, logging=False).reset_stats().simulate(395, logging=False)
print(net.results["profit"])                 # from 30 to 395
```

How a warm-up resets the statistics is explained in the [Statistics and Results](statistics.md) guide.

## Running replications in parallel

Replications do not depend on each other, so they can run at the same time on several processor cores, with Python's `concurrent.futures`.

```python
from concurrent.futures import ProcessPoolExecutor

def profit(args):
    s, seed = args
    return s, seed, run(s, seed)["profit"]

if __name__ == "__main__":
    with ProcessPoolExecutor() as pool:
        results = list(pool.map(profit, [(s, seed) for s in (60, 120) for seed in range(30)]))
```

Each run builds its own network inside its process, so a run gives the same result as when it runs alone. On Windows and macOS, each process starts Python afresh and imports your script. So put the functions at the top level of a script file, not in a notebook cell or inside another function, and start the pool under `if __name__ == "__main__":` as above. Starting the processes takes time, so this pays off only when the runs are long or many.
