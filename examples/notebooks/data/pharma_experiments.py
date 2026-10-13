"""Pharmacy case study experiments (case_study_pharma.ipynb) -- COMPUTE ONLY.

Runs the simulations behind the notebook's results on a many-core server, so
that the notebook and docs/case_study_pharma.md only have to plot them. The
model code is the notebook's own (daily review, cost per day after a 30-day
warm-up).

Experiments:
  - reps: s = 2000, S = 5000, run with R = 1000, 2000, 3000, 4000 and 5000
          replications (notebook cell 3).
  - grid: S = 1000, 2000, 3000, 4000 and 5000, with s from 100 up to S - 100 in
          steps of 100 and 1000 replications each (notebook cells 4 to 6; the
          S = 5000 row is also the confidence-interval plot of cell 4).

Each batch of replications is an independent task, run in parallel with
multiprocessing. Every task seeds NumPy from its own fixed seed, so a rerun
gives the same numbers whatever the number of workers.

Outputs (this directory):
  - pharma_reps_raw.csv      experiment,R,rep,cost_per_day,shortage_cost,waste_cost,holding_cost,ordering_cost,time_s
  - pharma_reps_summary.csv  R,n,exe_time_s,mean,std,std_err
  - pharma_grid_raw.csv      experiment,S,s,rep,cost_per_day,shortage_cost,waste_cost,holding_cost,ordering_cost,time_s
  - pharma_grid_summary.csv  S,s,n,mean,std,std_err
  Costs are per day, as in the notebook. std is np.std (as in the notebook),
  std_err = std / sqrt(n). exe_time_s is the sum of the replications' own run
  times, i.e. the time one core would need, not the wall-clock time.

Run (install SupplyNetPy 0.2.1 or later first: pip install "supplynetpy>=0.2.1"):
  QUICK=1 python pharma_experiments.py     # a few seconds; writes *_quick.csv to check the setup
  python pharma_experiments.py             # the full run, on all CPU cores
  NPROC=80 python pharma_experiments.py    # or cap the number of workers
"""
import os
import csv
import time
import multiprocessing as mp
from importlib import metadata

import numpy as np
import simpy
import SupplyNetPy.Components as scm

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
QUICK = os.environ.get("QUICK", "") not in ("", "0")
NPROC = int(os.environ.get("NPROC", "0")) or os.cpu_count()
HERE = os.path.dirname(os.path.abspath(__file__))
BASE_SEED = 2026

if QUICK:
    REPS_SWEEP = [10, 20]
    S_VALUES = [2000, 1000]
    S_STEP = 500
    GRID_REPS = 4
    REPS_PER_TASK = 2
    SUFFIX = "_quick"
else:
    REPS_SWEEP = [1000, 2000, 3000, 4000, 5000]
    S_VALUES = [5000, 4000, 3000, 2000, 1000]
    S_STEP = 100
    GRID_REPS = 1000
    REPS_PER_TASK = 50
    SUFFIX = ""

S_LOW = 100
REPS_S, REPS_BIG_S = 2000, 5000


# ----------------------------------------------------------------------------
# Model (from case_study_pharma.ipynb)
# ----------------------------------------------------------------------------
class Distributions:
    """
    Class to generate random numbers for demand (order quantity) and order arrival arrival times.
    Parameters:
        mu (float): Mean of the exponential distribution for order arrival times.
        lam (float): Lambda parameter of the Poisson distribution for demand (order quantity).
    """
    def __init__(self, mu=1, lam=1, p=0.01):
        self.mu = mu
        self.lam = lam
        self.p = p

    def poisson_demand(self):
        return np.random.poisson(self.lam)

    def expo_arrival(self):
        return np.random.exponential(self.mu)

    def geometric(self):
        return np.random.geometric(self.p, 1)[0]


def manufacturer_date_cal(time_now):
    """Calculate manufacturing date rounded down to the nearest month."""
    return time_now - (time_now % 30)


# Global parameters
T = 360     # number of days (360 days)
l = 6       # deterministic lead time (6 days)
e = 90      # shelf life of the drugs (3 months)
b = 5       # shortage cost (5 units)
z = 1       # waste cost (1 units)
h = 0.001   # holding cost (0.001 units)
o = 0.5     # ordering cost (0.5 units)
dt = 25     # demand on day t (Poisson 25/day)
yt_p = 0.01  # time until the next disruption ~ Geometric(p=0.01)
yt_r = 1/30  # recovery time ~ Geometric(p=1/30)
price = 1    # unit cost of drug


def setup_simulation(env, s, S, ini_level, st, disrupt_time, recovery_time):
    """Setup environment, supplier, distributor, link, and demand process."""
    supplier = scm.Supplier(env, "S1", "Supplier 1", "infinite_supplier",
                            node_disrupt_time=disrupt_time.geometric,
                            node_recovery_time=recovery_time.geometric)

    distributor = scm.InventoryNode(env, "D1", "Distributor 1", "distributor",
                                    capacity=float('inf'), initial_level=ini_level,
                                    inventory_holding_cost=h, inventory_type="perishable",
                                    manufacture_date=manufacturer_date_cal, shelf_life=e,
                                    replenishment_policy=scm.SSReplenishment,
                                    policy_param={'s': s, 'S': S, 'period': 1},
                                    product_buy_price=0, product_sell_price=price)

    link = scm.Link(env, "l1", supplier, distributor, cost=o, lead_time=lambda: l)

    demand = scm.Demand(env, "d1", "demand 1", order_arrival_model=lambda: 1,
                        order_quantity_model=st.poisson_demand, demand_node=distributor)

    return supplier, distributor, demand, link


def single_sim_run(S, s, ini_level):
    """Run a single simulation instance and return the cost per day and its parts."""
    env = simpy.Environment()
    st = Distributions(mu=1, lam=dt)
    disrupt_time = Distributions(p=yt_p)
    recovery_time = Distributions(p=yt_r)

    supplier, distributor, demand, link = setup_simulation(env, s, S, ini_level, st, disrupt_time, recovery_time)

    pharma_chain = scm.create_sc_net(env=env, nodes=[supplier, distributor], links=[link], demands=[demand])
    pharma_chain = scm.simulate_sc_net(pharma_chain, sim_time=30, logging=False)
    supplier.stats.reset()
    distributor.stats.reset()
    demand.stats.reset()
    pharma_chain = scm.simulate_sc_net(pharma_chain, sim_time=T, logging=False)

    shortage = distributor.stats.shortage[1]
    waste = distributor.stats.inventory_waste
    holding = distributor.stats.inventory_carry_cost
    transport = distributor.stats.transportation_cost

    total_cost = (shortage * b + waste * z + holding + transport)
    days = T - 30
    return {"cost_per_day": total_cost / days * price,
            "shortage_cost": shortage * b / days,
            "waste_cost": waste * z / days,
            "holding_cost": holding / days,
            "ordering_cost": transport / days}


# ----------------------------------------------------------------------------
# Tasks
# ----------------------------------------------------------------------------
def _worker_init():
    scm.global_logger.disable_logging()


def _task_seed(*key):
    return int(np.random.SeedSequence([BASE_SEED, *key]).generate_state(1)[0])


def _run_task(task):
    experiment, key, s, S, first_rep, n = task
    np.random.seed(_task_seed(1 if experiment == "reps" else 2, key, s, S, first_rep))
    rows = []
    for rep in range(first_rep, first_rep + n):
        t0 = time.perf_counter()
        result = single_sim_run(S=S, s=s, ini_level=S)
        row = {"experiment": experiment, "rep": rep}
        if experiment == "reps":
            row["R"] = key
        else:
            row["S"], row["s"] = S, s
        row.update({k: round(v, 6) for k, v in result.items()})
        row["time_s"] = round(time.perf_counter() - t0, 6)
        rows.append(row)
    return rows


def _chunks(experiment, key, s, S, reps):
    return [(experiment, key, s, S, first, min(REPS_PER_TASK, reps - first))
            for first in range(0, reps, REPS_PER_TASK)]


def write_csv(rows, path, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print("wrote %s (%d rows)" % (path, len(rows)))


def summarize(rows, group_keys):
    groups = {}
    for r in rows:
        groups.setdefault(tuple(r[k] for k in group_keys), []).append(r)
    out = []
    for key in sorted(groups):
        g = groups[key]
        costs = np.array([r["cost_per_day"] for r in g])
        row = dict(zip(group_keys, key))
        row.update({"n": len(g), "exe_time_s": round(sum(r["time_s"] for r in g), 3),
                    "mean": float(np.mean(costs)), "std": float(np.std(costs)),
                    "std_err": float(np.std(costs) / np.sqrt(len(g)))})
        out.append(row)
    return out


def _check_version():
    try:
        version = metadata.version("supplynetpy")
    except metadata.PackageNotFoundError:
        print("SupplyNetPy is not installed as a package; using", scm.__file__)
        return
    print("SupplyNetPy", version, "from", scm.__file__)
    if tuple(int(x) for x in version.split(".")[:3]) < (0, 2, 1):
        raise SystemExit("SupplyNetPy 0.2.1 or later is needed (a site could stop ordering "
                         "for good after a supplier disruption in earlier versions).")


if __name__ == "__main__":
    _check_version()
    t_start = time.perf_counter()
    tasks = []
    for R in REPS_SWEEP:
        tasks += _chunks("reps", R, REPS_S, REPS_BIG_S, R)
    for S in S_VALUES:
        for s in range(S_LOW, S, S_STEP):
            tasks += _chunks("grid", 0, s, S, GRID_REPS)
    n_runs = sum(t[5] for t in tasks)
    print("Running %d simulations in %d tasks on %d workers..." % (n_runs, len(tasks), NPROC))

    results, done = [], 0
    with mp.Pool(processes=NPROC, initializer=_worker_init) as pool:
        for rows in pool.imap_unordered(_run_task, tasks, chunksize=1):
            results.extend(rows)
            done += 1
            if done % max(1, len(tasks) // 20) == 0 or done == len(tasks):
                print("  %d/%d tasks done, %.1f min" % (done, len(tasks), (time.perf_counter() - t_start) / 60))

    parts = ["cost_per_day", "shortage_cost", "waste_cost", "holding_cost", "ordering_cost", "time_s"]
    reps_rows = sorted((r for r in results if r["experiment"] == "reps"), key=lambda r: (r["R"], r["rep"]))
    grid_rows = sorted((r for r in results if r["experiment"] == "grid"), key=lambda r: (-r["S"], r["s"], r["rep"]))
    write_csv(reps_rows, os.path.join(HERE, "pharma_reps_raw%s.csv" % SUFFIX), ["experiment", "R", "rep"] + parts)
    write_csv(grid_rows, os.path.join(HERE, "pharma_grid_raw%s.csv" % SUFFIX), ["experiment", "S", "s", "rep"] + parts)
    write_csv(summarize(reps_rows, ["R"]), os.path.join(HERE, "pharma_reps_summary%s.csv" % SUFFIX),
              ["R", "n", "exe_time_s", "mean", "std", "std_err"])
    write_csv([{k: v for k, v in r.items() if k != "exe_time_s"} for r in summarize(grid_rows, ["S", "s"])],
              os.path.join(HERE, "pharma_grid_summary%s.csv" % SUFFIX), ["S", "s", "n", "mean", "std", "std_err"])
    print("Total wall-clock: %.1f min" % ((time.perf_counter() - t_start) / 60))
