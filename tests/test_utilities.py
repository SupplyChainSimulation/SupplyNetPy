import pytest
import simpy
from unittest.mock import MagicMock, patch
import SupplyNetPy.Components.utilities as utilities

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
        self.shortage = [1, 10]
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
            "shortage": self.shortage,
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


def test_check_duplicate_id_accepts_set():
    """§5.2: ``check_duplicate_id`` accepts a ``set`` and inserts via ``.add``,
    giving O(1) membership checks for ``create_sc_net``'s internal use."""
    used_ids = set()
    utilities.check_duplicate_id(used_ids, "A", "ID")
    assert "A" in used_ids
    utilities.check_duplicate_id(used_ids, "B", "ID")
    assert used_ids == {"A", "B"}
    with pytest.raises(ValueError):
        utilities.check_duplicate_id(used_ids, "A", "node ID")


def test_check_duplicate_id_link_message_uses_entity_type():
    """Routing the inline object-branches through the helper fixes a copy/paste
    typo that previously raised ``"Duplicate node ID"`` for a duplicate
    *link*. The helper now interpolates ``entity_type`` into the message."""
    with pytest.raises(ValueError, match="Duplicate link ID"):
        utilities.check_duplicate_id({"L1"}, "L1", "link ID")

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


# ---------------------------------------------------------------------------
# Integration tests using real components (not DummyNode mocks).
#
# The tests above rely on DummyNode / DummyLink / DummyDemand, which are not
# subclasses of the real Node / Link / Demand. create_sc_net's `isinstance`
# branches silently skip them, so those tests verify shape only — they do not
# catch regressions in the wiring logic.  The tests below exercise create_sc_net
# end-to-end with real components so the full construct-and-simulate path is
# covered by automation.
# ---------------------------------------------------------------------------


import SupplyNetPy.Components as scm


def _intro_simple_netlist():
    return (
        [{"ID": "S1", "name": "Supplier1", "node_type": "infinite_supplier"},
         {"ID": "D1", "name": "Distributor1", "node_type": "distributor",
          "capacity": 150, "initial_level": 50, "inventory_holding_cost": 0.2,
          "replenishment_policy": scm.SSReplenishment,
          "policy_param": {"s": 100, "S": 150},
          "product_buy_price": 100, "product_sell_price": 105}],
        [{"ID": "L1", "source": "S1", "sink": "D1", "cost": 5, "lead_time": lambda: 2}],
        [{"ID": "d1", "name": "Demand1", "order_arrival_model": lambda: 1,
          "order_quantity_model": lambda: 10, "demand_node": "D1"}],
    )


def test_create_sc_net_real_dicts_wires_real_objects():
    nodes, links, demands = _intro_simple_netlist()
    sc = utilities.create_sc_net(nodes, links, demands)
    # Real components, not mocks:
    assert isinstance(sc["nodes"]["S1"], scm.Supplier)
    assert isinstance(sc["nodes"]["D1"], scm.InventoryNode)
    assert isinstance(sc["links"]["L1"], scm.Link)
    assert isinstance(sc["demands"]["d1"], scm.Demand)
    # Counts are populated:
    assert sc["num_suppliers"] == 1
    assert sc["num_distributors"] == 1
    assert sc["num_of_nodes"] == 2
    assert sc["num_of_links"] == 1
    # Link is registered on the sink's suppliers list (Link.__init__ side-effect):
    assert sc["links"]["L1"] in sc["nodes"]["D1"].suppliers


def test_create_sc_net_objects_style_round_trip():
    env = simpy.Environment()
    s = scm.Supplier(env=env, ID="Sx", name="Sx", node_type="infinite_supplier", logging=False)
    d = scm.InventoryNode(env=env, ID="Dx", name="Dx", node_type="distributor",
                          capacity=150, initial_level=50, inventory_holding_cost=0.2,
                          replenishment_policy=scm.SSReplenishment,
                          policy_param={"s": 100, "S": 150},
                          product_buy_price=100, product_sell_price=105, logging=False)
    l = scm.Link(env=env, ID="Lx", source=s, sink=d, cost=5, lead_time=lambda: 2)
    dem = scm.Demand(env=env, ID="dx", name="dx", order_arrival_model=lambda: 1,
                     order_quantity_model=lambda: 10, demand_node=d, logging=False)
    sc = utilities.create_sc_net(nodes=[s, d], links=[l], demands=[dem], env=env)
    assert sc["nodes"]["Sx"] is s
    assert sc["nodes"]["Dx"] is d
    assert sc["links"]["Lx"] is l
    assert sc["demands"]["dx"] is dem


def test_create_sc_net_requires_env_for_objects():
    env = simpy.Environment()
    s = scm.Supplier(env=env, ID="Sy", name="Sy", node_type="infinite_supplier", logging=False)
    # When nodes[0] is a real Node instance and env is omitted, must raise.
    with pytest.raises(ValueError):
        utilities.create_sc_net(nodes=[s], links=[], demands=[])


def test_simulate_sc_net_returns_canonical_intro_simple_numbers():
    nodes, links, demands = _intro_simple_netlist()
    sc = utilities.create_sc_net(nodes, links, demands)
    result = utilities.simulate_sc_net(sc, sim_time=20, logging=False)
    # Locks the canonical intro_simple.py scenario output at the network level:
    assert result["profit"] == -4435.0
    assert result["revenue"] == 21000
    assert result["total_cost"] == 25435.0
    assert result["transportation_cost"] == 25
    assert result["shortage"] == [0, 0]
    assert result["backorders"] == [0, 0]
    assert result["num_of_nodes"] == 2
    assert result["num_of_links"] == 1


def test_create_sc_net_duplicate_link_id_raises():
    env = simpy.Environment()
    nodes = [{"ID": "S1", "name": "S", "node_type": "infinite_supplier"},
             {"ID": "D1", "name": "D", "node_type": "distributor",
              "capacity": 100, "initial_level": 50, "inventory_holding_cost": 0.1,
              "replenishment_policy": None, "policy_param": None,
              "product_sell_price": 5, "product_buy_price": 2}]
    links = [{"ID": "L1", "source": "S1", "sink": "D1", "cost": 1, "lead_time": lambda: 1},
             {"ID": "L1", "source": "S1", "sink": "D1", "cost": 1, "lead_time": lambda: 1}]
    demands = [{"ID": "d1", "name": "d", "order_arrival_model": lambda: 1,
                "order_quantity_model": lambda: 5, "demand_node": "D1"}]
    with pytest.raises(ValueError):
        utilities.create_sc_net(nodes, links, demands, env=env)


def test_create_sc_net_invalid_link_endpoint_raises():
    nodes = [{"ID": "S1", "name": "S", "node_type": "infinite_supplier"},
             {"ID": "D1", "name": "D", "node_type": "distributor",
              "capacity": 100, "initial_level": 50, "inventory_holding_cost": 0.1,
              "replenishment_policy": None, "policy_param": None,
              "product_sell_price": 5, "product_buy_price": 2}]
    # "GHOST" isn't defined in nodes — must raise.
    links = [{"ID": "L1", "source": "GHOST", "sink": "D1", "cost": 1, "lead_time": lambda: 1}]
    demands = [{"ID": "d1", "name": "d", "order_arrival_model": lambda: 1,
                "order_quantity_model": lambda: 5, "demand_node": "D1"}]
    with pytest.raises(ValueError):
        utilities.create_sc_net(nodes, links, demands)


# §4.5: create_sc_net must validate both construction styles consistently.
# Previously only ``nodes[0]`` / ``links[0]`` / ``demands[0]`` were checked to
# decide whether env was required, so a dict at index 0 followed by a Node
# instance at a later index silently bypassed the env check.


def test_create_sc_net_mixed_nodes_dict_and_object_raises():
    env = simpy.Environment()
    obj_supplier = scm.Supplier(env=env, ID="S2", name="S2", node_type="infinite_supplier", logging=False)
    # nodes[0] is a dict, nodes[1] is a real Node instance — must be rejected.
    nodes = [{"ID": "S1", "name": "S1", "node_type": "infinite_supplier"}, obj_supplier]
    links = [{"ID": "L1", "source": "S1", "sink": "S2", "cost": 1, "lead_time": lambda: 1}]
    demands = [{"ID": "d1", "name": "d", "order_arrival_model": lambda: 1,
                "order_quantity_model": lambda: 5, "demand_node": "S2"}]
    with pytest.raises(ValueError, match="mixes dicts"):
        utilities.create_sc_net(nodes, links, demands, env=env)


def test_create_sc_net_object_at_nonzero_index_still_requires_env():
    env = simpy.Environment()
    # Links list has an object at index 1; nodes/demands are all dicts.  Pre-fix,
    # ``links[0]`` being a dict meant the env-required guard did not fire even
    # though the object at links[1] belonged to a different env. Post-fix, the
    # whole list is scanned so this mix is rejected outright.
    nodes = [{"ID": "S1", "name": "S1", "node_type": "infinite_supplier"},
             {"ID": "D1", "name": "D1", "node_type": "distributor",
              "capacity": 100, "initial_level": 0, "inventory_holding_cost": 0.1,
              "replenishment_policy": None, "policy_param": None,
              "product_sell_price": 5, "product_buy_price": 2}]
    # A dummy real Link object — we cannot construct it against "S1"/"D1" dicts,
    # so use a parallel env + parallel nodes purely for the validator to reject.
    other_env = simpy.Environment()
    other_s = scm.Supplier(env=other_env, ID="Sx", name="Sx", node_type="infinite_supplier", logging=False)
    other_d = scm.InventoryNode(env=other_env, ID="Dx", name="Dx", node_type="distributor",
                                capacity=100, initial_level=0, inventory_holding_cost=0.1,
                                replenishment_policy=None, policy_param=None,
                                product_sell_price=5, product_buy_price=2, logging=False)
    other_link = scm.Link(env=other_env, ID="Lx", source=other_s, sink=other_d, cost=1, lead_time=lambda: 1)
    links = [{"ID": "L1", "source": "S1", "sink": "D1", "cost": 1, "lead_time": lambda: 1}, other_link]
    demands = [{"ID": "d1", "name": "d", "order_arrival_model": lambda: 1,
                "order_quantity_model": lambda: 5, "demand_node": "D1"}]
    with pytest.raises(ValueError, match="mixes dicts"):
        utilities.create_sc_net(nodes, links, demands, env=env)


def test_create_sc_net_shop_node_type_end_to_end():
    # §4.7: "shop" was previously a latent bug — create_sc_net's dispatch
    # ladder accepted it as a retailer, but Node.__init__'s hard-coded valid
    # list did not include "shop", so the object construction itself raised
    # ValueError. After unifying both against the NodeType enum (which lists
    # "shop"), the end-to-end path works.
    nodes = [{"ID": "SUP", "name": "S", "node_type": "infinite_supplier"},
             {"ID": "SHP", "name": "ShopX", "node_type": "shop",
              "capacity": 100, "initial_level": 50, "inventory_holding_cost": 0.1,
              "replenishment_policy": None, "policy_param": None,
              "product_sell_price": 5, "product_buy_price": 2}]
    links = [{"ID": "L1", "source": "SUP", "sink": "SHP", "cost": 1, "lead_time": lambda: 1}]
    demands = [{"ID": "d1", "name": "d", "order_arrival_model": lambda: 1,
                "order_quantity_model": lambda: 5, "demand_node": "SHP"}]
    sc = utilities.create_sc_net(nodes, links, demands)
    assert sc["nodes"]["SHP"].node_type == "shop"
    assert sc["num_retailers"] == 1


def test_create_sc_net_object_env_must_match():
    env = simpy.Environment()
    other_env = simpy.Environment()
    # Object built against ``other_env`` but passed to create_sc_net with ``env``.
    # Pre-fix this was silently accepted and the object's env was left dangling;
    # post-fix it must raise.
    s = scm.Supplier(env=other_env, ID="Sz", name="Sz", node_type="infinite_supplier", logging=False)
    d = scm.InventoryNode(env=other_env, ID="Dz", name="Dz", node_type="distributor",
                          capacity=100, initial_level=0, inventory_holding_cost=0.1,
                          replenishment_policy=None, policy_param=None,
                          product_sell_price=5, product_buy_price=2, logging=False)
    l = scm.Link(env=other_env, ID="Lz", source=s, sink=d, cost=1, lead_time=lambda: 1)
    dem = scm.Demand(env=other_env, ID="dz", name="dz", order_arrival_model=lambda: 1,
                     order_quantity_model=lambda: 5, demand_node=d, logging=False)
    with pytest.raises(ValueError, match="env does not match"):
        utilities.create_sc_net(nodes=[s, d], links=[l], demands=[dem], env=env)