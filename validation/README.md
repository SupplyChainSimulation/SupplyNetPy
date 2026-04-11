# Validation by comparing with a commercial tool

This validation was carried out to verify the correctness of SupplyNetPy's components and replenishment policies. [AnyLogistix](https://www.anylogistix.com/) (free, personal learning edition) was used as the reference. AnyLogistix provides supply chain-specific components and comprehensive documentation. We design and configure a minimal supply chain network model (a single distributor replenishing from an infinite-capacity supplier, facing deterministic daily demand), which enables us to isolate components and easily compare and assess their correctness in SupplyNetPy. We have experimented with all types of nodes and inventory replenishment policies to compare their behavior, and we have updated the component to be more flexible in SupplyNetPy.

Below, we describe a few models and their configurations, and the detailed performance comparison is listed in the file `validation_snp_anylogistix_cmp.csv`.

## Setup

```bash
pip install supplynetpy simpy numpy matplotlib
```

```python
import SupplyNetPy as scm
import simpy
```

## Common Parameters

These apply to all models unless stated otherwise:

- Single product: `buy_price=150`, `sell_price=300`
- Supplier S1: `node_type="infinite_supplier"` (omitted from tables)
- All distributor nodes: `inventory_holding_cost=0.22`, `product_buy_price=150`, `product_sell_price=300`
- Demand `delivery_cost` and `lead_time` always match the link's cost and lead_time (omitted from tables)
- In Models 6–8, `initial_level = capacity` for all distributor nodes (shown as one column)

---

## Model 1: 1 Supplier → 1 Distributor (RQ, lead time = 2)

`simtime = 59` | Link S1→D1: cost=10, lead_time=2

| ID | Type | Policy (Params) | Order Qty | Interval |
|----|------|-----------------|-----------|----------|
| D1 | Distributor | RQ (R=500, Q=500) | NA | NA |
| d1 | Demand → D1 | NA | 120 | 2 |

---

## Model 2: 1 Supplier → 1 Distributor, 2 Demands (RQ, lead time = 2)

`simtime = 59` | Link S1→D1: cost=10, lead_time=2

| ID | Type | Policy (Params) | Order Qty | Interval |
|----|------|-----------------|-----------|----------|
| D1 | Distributor | RQ (R=500, Q=500) | NA | NA |
| d1 | Demand → D1 | NA | 120 | 2 |
| d2 | Demand → D1 | NA | 80 | 2 |

---

## Model 3: 1 Supplier → 1 Distributor (SS, lead time = 2)

`simtime = 59` | Link S1→D1: cost=10, lead_time=2

| ID | Type | Policy (Params) | Order Qty | Interval |
|----|------|-----------------|-----------|----------|
| D1 | Distributor | SS (s=200, S=500) | NA | NA |
| d1 | Demand → D1 | NA | 120 | 2 |

---

## Model 4: 1 Supplier → 1 Distributor, 2 Demands (SS with safety stock, lead time = 1)

`simtime = 59` | Link S1→D1: cost=10, lead_time=1

| ID | Type | Policy (Params) | Order Qty | Interval |
|----|------|-----------------|-----------|----------|
| D1 | Distributor | SS (s=200, S=500, safety=100) | NA | NA |
| d1 | Demand → D1 | NA | 120 | 2 |
| d2 | Demand → D1 | NA | 80 | 2 |

---

## Model 5: 1 Supplier → 1 Distributor (TQ periodic review, lead time = 1)

`simtime = 59` | Link S1→D1: cost=10, lead_time=1

| ID | Type | Policy (Params) | Order Qty | Interval |
|----|------|-----------------|-----------|----------|
| D1 | Distributor | TQ (T=2, Q=500) | NA | NA |
| d1 | Demand → D1 | NA | 120 | 2 |

---

## Model 6: 1 Supplier → 2 Distributors (SS + RQ, lead time = 5)

`simtime = 31` | Links S1→D1, S1→D2: cost=10, lead_time=5 each

| ID | Type | Cap/Init | Policy (Params) | Node | Order Qty | Interval |
|----|------|----------|-----------------|------|-----------|----------|
| D1 | Distributor | 1000 | SS (s=400, S=1000) | NA | NA | NA |
| D2 | Distributor | 1500 | RQ (R=1000, Q=500) | NA | NA | NA |
| demand_D1 | Demand | NA | NA | D1 | 400 | 1 |
| demand_D2 | Demand | NA | NA | D1 | 400 | 1 |
| demand_D3 | Demand | NA | NA | D2 | 60 | 2 |
| demand_D4 | Demand | NA | NA | D2 | 80 | 2 |

---

## Model 7: 1 Supplier → 4 Distributors (SS + RQ, lead time = 1)

`simtime = 31` | Links S1→D1/D2/D3/D4: cost=20, lead_time=1 each

| ID | Type | Cap/Init | Policy (Params) | Node | Order Qty | Interval |
|----|------|----------|-----------------|------|-----------|----------|
| D1 | Distributor | 1000 | SS (s=500, S=1000) | NA | NA | NA |
| D2 | Distributor | 1500 | SS (s=1000, S=1500) | NA | NA | NA |
| D3 | Distributor | 2000 | RQ (R=1000, Q=1000) | NA | NA | NA |
| D4 | Distributor | 2500 | RQ (R=1500, Q=1000) | NA | NA | NA |
| demand_D1 | Demand | NA | NA | D1 | 20 | 1 |
| demand_D2 | Demand | NA | NA | D1 | 40 | 1 |
| demand_D3 | Demand | NA | NA | D2 | 60 | 2 |
| demand_D4 | Demand | NA | NA | D2 | 80 | 2 |
| demand_D5 | Demand | NA | NA | D3 | 100 | 3 |
| demand_D6 | Demand | NA | NA | D3 | 120 | 3 |
| demand_D7 | Demand | NA | NA | D4 | 140 | 4 |
| demand_D8 | Demand | NA | NA | D4 | 160 | 4 |

---

## Model 8: 1 Supplier → 8 Distributors (SS + RQ, lead time = 0.5)

`simtime = 31` | Links S1→D1…D8: cost=30, lead_time=0.5 each

| ID | Type | Cap/Init | Policy (Params) | Node | Order Qty | Interval |
|----|------|----------|-----------------|------|-----------|----------|
| D1 | Distributor | 1000 | SS (s=500, S=1000) | NA | NA | NA |
| D2 | Distributor | 1500 | SS (s=1000, S=1500) | NA | NA | NA |
| D3 | Distributor | 2000 | SS (s=1500, S=2000) | NA | NA | NA |
| D4 | Distributor | 2500 | SS (s=2000, S=2500) | NA | NA | NA |
| D5 | Distributor | 3000 | RQ (R=1500, Q=1500) | NA | NA | NA |
| D6 | Distributor | 3500 | RQ (R=2000, Q=1500) | NA | NA | NA |
| D7 | Distributor | 4000 | RQ (R=2000, Q=2000) | NA | NA | NA |
| D8 | Distributor | 4500 | RQ (R=2500, Q=2000) | NA | NA | NA |
| demand_D1 | Demand | NA | NA | D1 | 20 | 1 |
| demand_D2 | Demand | NA | NA | D1 | 40 | 1 |
| demand_D3 | Demand | NA | NA | D2 | 60 | 2 |
| demand_D4 | Demand | NA | NA | D2 | 80 | 2 |
| demand_D5 | Demand | NA | NA | D3 | 100 | 3 |
| demand_D6 | Demand | NA | NA | D3 | 120 | 3 |
| demand_D7 | Demand | NA | NA | D4 | 140 | 4 |
| demand_D8 | Demand | NA | NA | D4 | 160 | 4 |
| demand_D9 | Demand | NA | NA | D5 | 180 | 5 |
| demand_D10 | Demand | NA | NA | D5 | 200 | 5 |
| demand_D11 | Demand | NA | NA | D6 | 220 | 6 |
| demand_D12 | Demand | NA | NA | D6 | 240 | 6 |
| demand_D13 | Demand | NA | NA | D7 | 260 | 7 |
| demand_D14 | Demand | NA | NA | D7 | 280 | 7 |
| demand_D15 | Demand | NA | NA | D8 | 300 | 8 |
| demand_D16 | Demand | NA | NA | D8 | 320 | 8 |

---

## Model 9: 1 Supplier → 1 Distributor, 2 Demands (TQ, lead time = 5, non-integer demand intervals)

> **Note:** This is a pathological case — non-integer demand inter-arrival intervals (0.3, 0.2) trigger both simultaneous-event ordering (Case A: the T=1 review period coincides with demand_D2 arrivals at integer times, e.g. t=1.0, 2.0, …) and floating-point accumulation (Case B). Differences between SupplyNetPy and AnyLogistix are expected and are not regressions. Notebook: `snp_anylogistix_cmp.ipynb`.

`simtime = 20` | Link S1→D1: cost=10, lead_time=5 | D1: capacity=700, initial_level=500, inventory_holding_cost=0.2, product_buy_price=30, product_sell_price=50

| ID | Type | Policy (Params) | Order Qty | Interval |
|----|------|-----------------|-----------|----------|
| D1 | Distributor | TQ (T=1, Q=400) | NA | NA |
| demand_D1 | Demand → D1 | NA | 60 | 0.3 |
| demand_D2 | Demand → D1 | NA | 40 | 0.2 |
