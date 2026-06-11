"""Performance benchmark for SupplyNetPy (WSC 2026 paper, Section 5.2) -- COMPUTE ONLY.

Resolves reviewer comment R1-4: the original benchmark regenerated a new random
network per run, so variance at large N was dominated by network randomness
rather than execution time.

Design:
  - The network is FIXED per N (deterministic structure/attributes); replications
    vary only the simulation RNG, removing structural variance.
  - Each (sweep, N, L, replication) is an INDEPENDENT task, run in parallel via
    multiprocessing (intended for a many-core server).
  - This script writes RAW per-replication samples to CSV only. No plotting and no
    summary statistics here; plotting/boxplots/CIs are produced separately by
    plot_performance.py from these CSVs.

Outputs (this directory):
  - perform_n_raw.csv       columns: sweep,N,L,rep,time_s   (vs N, fixed L)
  - perform_sim_l_raw.csv   columns: sweep,N,L,rep,time_s   (vs L, fixed N)

Run:
  python benchmark_performance.py            # uses all CPU cores
  NPROC=80 python benchmark_performance.py   # or set the env var to cap workers
"""
import os
import gc
import csv
import time
import random
import multiprocessing as mp

import SupplyNetPy.Components as scm
from SupplyNetPy.Components.core import RawMaterial, Product

# ----------------------------------------------------------------------------
# Configuration (edit ranges/replications freely; runs are independent)
# ----------------------------------------------------------------------------
REPS = 30                                              # replications per config
N_SWEEP = [50, 100, 200, 350, 500, 750, 1000, 1500, 2000]   # vs N, at fixed L
L_FIXED = 500
L_SWEEP = [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000]  # vs L, at fixed N
N_FIXED = 50

NPROC = int(os.environ.get("NPROC", "0")) or os.cpu_count()
HERE = os.path.dirname(os.path.abspath(__file__))


# ----------------------------------------------------------------------------
# Network generation: fixed topology for a given N (deterministic structure).
# Proportions follow the paper: ~1/5 suppliers, ~1/10 manufacturers,
# ~1/7 distributors, remainder retailers. All-to-all between consecutive
# echelons; infinite-capacity suppliers; exponential-interarrival demand at
# each retailer.
# ----------------------------------------------------------------------------
def build_network(N, fanin=None):
    """fanin=None -> all-to-all between echelons; fanin=k -> each downstream
    node connects to k upstream nodes (round-robin), giving links linear in N."""
    n_sup = max(1, N // 5)
    n_man = max(1, N // 10)
    n_dis = max(1, N // 7)
    n_ret = max(1, N - n_sup - n_man - n_dis)

    rm = RawMaterial(ID="RM", name="raw", extraction_quantity=1000,
                     extraction_time=1, mining_cost=1, cost=2)

    nodes, links, demands = [], [], []
    sup_ids, man_ids, dis_ids, ret_ids = [], [], [], []

    for i in range(n_sup):
        sid = "S%d" % i
        sup_ids.append(sid)
        nodes.append({"ID": sid, "name": sid, "node_type": "infinite_supplier",
                      "raw_material": rm})
    for i in range(n_man):
        mid = "M%d" % i
        man_ids.append(mid)
        prod = Product(ID="P%d" % i, name="prod", manufacturing_cost=1,
                       manufacturing_time=1, sell_price=15,
                       raw_materials=[(rm, 1)], batch_size=100)
        nodes.append({"ID": mid, "name": mid, "node_type": "manufacturer",
                      "capacity": 1000, "initial_level": 200,
                      "inventory_holding_cost": 0.5, "product_sell_price": 15,
                      "replenishment_policy": scm.SSReplenishment,
                      "policy_param": {"s": 200, "S": 800}, "product": prod})
    for i in range(n_dis):
        did = "D%d" % i
        dis_ids.append(did)
        nodes.append({"ID": did, "name": did, "node_type": "distributor",
                      "capacity": 500, "initial_level": 150,
                      "inventory_holding_cost": 0.5,
                      "replenishment_policy": scm.SSReplenishment,
                      "policy_param": {"s": 100, "S": 400},
                      "product_buy_price": 10, "product_sell_price": 13})
    for i in range(n_ret):
        rid = "R%d" % i
        ret_ids.append(rid)
        nodes.append({"ID": rid, "name": rid, "node_type": "retailer",
                      "capacity": 200, "initial_level": 80,
                      "inventory_holding_cost": 0.5,
                      "replenishment_policy": scm.SSReplenishment,
                      "policy_param": {"s": 40, "S": 150},
                      "product_buy_price": 13, "product_sell_price": 18})

    def connect(src_ids, dst_ids):
        for j, b in enumerate(dst_ids):
            if fanin is None:
                chosen = src_ids
            else:
                k = min(fanin, len(src_ids))
                chosen = [src_ids[(j + t) % len(src_ids)] for t in range(k)]
            for a in chosen:
                links.append({"ID": "L_%s_%s" % (a, b), "source": a, "sink": b,
                              "cost": 3,
                              "lead_time": (lambda: random.expovariate(1 / 3))})

    connect(sup_ids, man_ids)
    connect(man_ids, dis_ids)
    connect(dis_ids, ret_ids)

    for rid in ret_ids:
        demands.append({"ID": "d_%s" % rid, "name": "dem",
                        "order_arrival_model": (lambda: random.expovariate(1)),
                        "order_quantity_model": (lambda: 10),
                        "demand_node": rid})
    return nodes, links, demands


# Per-worker cache so a fixed network is built once per N per process, then
# reused across that N's replications (only the simulation RNG varies).
_NET_CACHE = {}


def _get_net(N):
    if N not in _NET_CACHE:
        _NET_CACHE[N] = build_network(N)
    return _NET_CACHE[N]


def _run_task(task):
    sweep, N, L, rep = task
    nodes, links, demands = _get_net(N)
    random.seed(rep)  # fixed network; only the simulation RNG varies per rep
    net = scm.create_sc_net(nodes, links, demands)
    gc.collect()
    gc.disable()
    t0 = time.perf_counter()
    scm.simulate_sc_net(net, sim_time=L, logging=False)
    dt = time.perf_counter() - t0
    gc.enable()
    return {"sweep": sweep, "N": N, "L": L, "rep": rep, "time_s": round(dt, 6)}


def write_csv(rows, path):
    rows = sorted(rows, key=lambda r: (r["N"], r["L"], r["rep"]))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sweep", "N", "L", "rep", "time_s"])
        w.writeheader()
        w.writerows(rows)
    print("wrote %s (%d rows)" % (path, len(rows)))


if __name__ == "__main__":
    t_start = time.perf_counter()
    tasks_a = [("N", N, L_FIXED, r) for N in N_SWEEP for r in range(REPS)]
    tasks_b = [("L", N_FIXED, L, r) for L in L_SWEEP for r in range(REPS)]
    all_tasks = tasks_a + tasks_b
    print("Running %d tasks on %d workers..." % (len(all_tasks), NPROC))

    with mp.Pool(processes=NPROC) as pool:
        results = pool.map(_run_task, all_tasks, chunksize=1)

    write_csv([r for r in results if r["sweep"] == "N"],
              os.path.join(HERE, "perform_n_raw.csv"))
    write_csv([r for r in results if r["sweep"] == "L"],
              os.path.join(HERE, "perform_sim_l_raw.csv"))
    print("Total wall-clock: %.1f min" % ((time.perf_counter() - t_start) / 60))
