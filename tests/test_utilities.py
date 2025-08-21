import pytest
import simpy
from unittest.mock import MagicMock, patch
import SupplyNetPy.Components.utilities as utilities

# Import the functions to test

# Dummy classes to mock core.py dependencies
class DummyStats:
    def __init__(self):
        self.inventory_spend_cost = 10
        self.inventory_waste = 2
        self.transportation_cost = 5
        self.node_cost = 20
        self.revenue = 50
        self.demand_placed = [3, 30]
        self.fulfillment_received = [2, 20]
        self.orders_shortage = [1, 10]
        self.backorder = [0, 0]
    def update_stats(self):
        pass
    def get_statistics(self):
        return {
            "inventory_spend_cost": self.inventory_spend_cost,
            "inventory_waste": self.inventory_waste,
            "transportation_cost": self.transportation_cost,
            "node_cost": self.node_cost,
            "revenue": self.revenue,
            "demand_placed": self.demand_placed,
            "fulfillment_received": self.fulfillment_received,
            "orders_shortage": self.orders_shortage,
            "backorder": self.backorder,
        }

class DummyInventory:
    def __init__(self):
        self.inventory = MagicMock(level=100)
        self.instantaneous_levels = [(0, 100), (1, 200)]
        self.carry_cost = 15

class DummyNode:
    def __init__(self, ID, node_type, name="Node"):
        self.ID = ID
        self.node_type = node_type
        self.name = name
        self.inventory = DummyInventory()
        self.stats = DummyStats()
    def get_info(self):
        return {"ID": self.ID, "node_type": self.node_type, "name": self.name}

class DummyLink:
    def __init__(self, ID, source, sink):
        self.ID = ID
        self.source = source
        self.sink = sink
    def get_info(self):
        return {"ID": self.ID, "source": self.source.ID, "sink": self.sink.ID}
    def lead_time(self):
        return 2.5

class DummyDemand:
    def __init__(self, ID, demand_node):
        self.ID = ID
        self.demand_node = demand_node
        self.stats = DummyStats()
    def get_info(self):
        return {"ID": self.ID, "demand_node": self.demand_node.ID}

class DummyLogger:
    def __init__(self):
        self.logged = []
    def error(self, msg): self.logged.append(("error", msg))
    def info(self, msg): self.logged.append(("info", msg))
    def warning(self, msg): self.logged.append(("warning", msg))

class DummyGlobalLogger:
    def __init__(self):
        self.logger = DummyLogger()
    def enable_logging(self, log_to_screen=True): pass
    def disable_logging(self): pass

def test_check_duplicate_id_no_duplicate():
    used_ids = []
    utilities.check_duplicate_id(used_ids, "A", "ID")
    assert "A" in used_ids

def test_check_duplicate_id_duplicate():
    used_ids = ["A"]
    with pytest.raises(ValueError):
        utilities.check_duplicate_id(used_ids, "A", "node ID")

def test_process_info_dict_logs_and_returns(monkeypatch):
    logger = DummyLogger()
    info = {"a": 1, "b": lambda: None}
    result = utilities.process_info_dict(info, logger)
    assert "a: 1" in result
    assert "b:" in result
    assert any("a: 1" in msg for typ, msg in logger.logged)
    assert any("b:" in msg for typ, msg in logger.logged)

def test_visualize_sc_net_runs(monkeypatch):
    # Patch plt.show to avoid opening a window
    monkeypatch.setattr(utilities.plt, "show", lambda: None)
    nodes = {"N1": DummyNode("N1", "supplier"), "N2": DummyNode("N2", "retailer")}
    links = {"L1": DummyLink("L1", nodes["N1"], nodes["N2"])}
    scnet = {"nodes": nodes, "links": links}
    utilities.visualize_sc_net(scnet)  # Should not raise

def test_get_sc_net_info_returns_string():
    nodes = {"N1": DummyNode("N1", "supplier")}
    links = {"L1": DummyLink("L1", nodes["N1"], nodes["N1"])}
    demands = {"D1": DummyDemand("D1", nodes["N1"])}
    scnet = {
        "nodes": nodes,
        "links": links,
        "demands": demands,
        "num_of_nodes": 1,
        "num_of_links": 1,
        "num_suppliers": 1,
        "num_manufacturers": 0,
        "num_distributors": 0,
        "num_retailers": 0,
        "extra_metric": 123
    }
    result = utilities.get_sc_net_info(scnet)
    assert "Supply chain configuration" in result
    assert "Nodes in the network" in result
    assert "Edges in the network" in result
    assert "Demands in the network" in result
    assert "extra_metric: 123" in result

def test_create_sc_net_with_dicts():
    nodes = [{"ID": "N1", "node_type": "infinite_supplier", "name": "S1"},
             {"ID": "N2", "node_type": "warehouse", "name": "R1", "capacity": 100,
              "initial_level": 50, "inventory_holding_cost": 1.0, "product_sell_price": 10.0,
              "product_buy_price": 5.0, "replenishment_policy": None, "policy_param": None}
            ]
    links = [{"ID": "L1", "source": "N1", "sink": "N2", "lead_time": lambda:2.5, "cost": 1.0}]
    demands = [{"ID": "D1", "demand_node": "N2",  "name":"d1", "order_quantity_model": lambda: 10, "order_arrival_model": lambda: 5}]
    scnet = utilities.create_sc_net(nodes, links, demands)
    assert "nodes" in scnet and "links" in scnet and "demands" in scnet
    assert scnet["num_suppliers"] == 1

def test_create_sc_net_with_objects():
    env = simpy.Environment()
    n = DummyNode("N1", "supplier")
    l = DummyLink("L1", n, n)
    d = DummyDemand("D1", n)
    scnet = utilities.create_sc_net([n], [l], [d], env=env)
    assert "nodes" in scnet and "links" in scnet and "demands" in scnet

def test_create_sc_net_invalid_node_type():
    env = simpy.Environment()
    nodes = [{"ID": "N1", "node_type": "invalid", "name": "S1"},
             {"ID": "N2", "node_type": "warehouse", "name": "R1", "capacity": 100,
              "initial_level": 50, "inventory_holding_cost": 1.0, "product_sell_price": 10.0,
              "product_buy_price": 5.0, "replenishment_policy": None, "policy_param": None}
            ]
    links = [{"ID": "L1", "source": "N1", "sink": "N2", "lead_time": lambda:2.5, "cost": 1.0}]
    demands = [{"ID": "D1", "demand_node": "N2",  "name":"d1", "order_quantity_model": lambda: 10, "order_arrival_model": lambda: 5}]
    with pytest.raises(ValueError):
        utilities.create_sc_net(nodes, links, demands)

def test_create_sc_net_duplicate_id():
    nodes = [{"ID": "N1", "node_type": "infinite_supplier", "name": "S1"},
             {"ID": "N1", "node_type": "warehouse", "name": "R1", "capacity": 100,
              "initial_level": 50, "inventory_holding_cost": 1.0, "product_sell_price": 10.0,
              "product_buy_price": 5.0, "replenishment_policy": None, "policy_param": None}
            ]
    links = [{"ID": "L1", "source": "N1", "sink": "N2", "lead_time": lambda:2.5, "cost": 1.0}]
    demands = [{"ID": "D1", "demand_node": "N2",  "name":"d1", "order_quantity_model": lambda: 10, "order_arrival_model": lambda: 5}]
    with pytest.raises(ValueError):
        utilities.create_sc_net(nodes, links, demands)

def test_simulate_sc_net_basic(monkeypatch):
    env = simpy.Environment()
    n = DummyNode("N1", "supplier")
    l = DummyLink("L1", n, n)
    d = DummyDemand("D1", n)
    scnet = utilities.create_sc_net([n], [l], [d], env=env)
    result = utilities.simulate_sc_net(scnet, 10)
    assert "profit" in result
    assert "total_cost" in result

def test_simulate_sc_net_with_logging_tuple(monkeypatch):
    env = simpy.Environment()
    n = DummyNode("N1", "supplier")
    l = DummyLink("L1", n, n)
    d = DummyDemand("D1", n)
    scnet = utilities.create_sc_net([n], [l], [d], env=env)
    result = utilities.simulate_sc_net(scnet, 10, logging=(2, 5))
    assert "profit" in result

def test_simulate_sc_net_warns_if_sim_time_less(monkeypatch):
    env = simpy.Environment()
    n = DummyNode("N1", "supplier")
    l = DummyLink("L1", n, n)
    d = DummyDemand("D1", n)
    scnet = utilities.create_sc_net([n], [l], [d], env=env)
    scnet["env"].run(5)
    result = utilities.simulate_sc_net(scnet, 3)
    assert "profit" in result

def test_print_node_wise_performance_prints(capsys):
    n1 = DummyNode("N1", "supplier", name="Node1")
    n2 = DummyNode("N2", "retailer", name="Node2")
    utilities.print_node_wise_performance([n1, n2])
    out = capsys.readouterr().out
    assert "Performance Metric" in out
    assert "Node1" in out and "Node2" in out

def test_print_node_wise_performance_empty(capsys):
    utilities.print_node_wise_performance([])
    out = capsys.readouterr().out
    assert "No nodes provided." in out