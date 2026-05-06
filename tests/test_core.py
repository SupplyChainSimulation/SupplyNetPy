import random
import unittest
import pytest
import simpy
import SupplyNetPy.Components as scm

# §7: per-test SimPy environments — see :func:`_fresh_env` and the per-class
# ``setUp`` methods below. The previous module-level ``env = simpy.Environment()``
# leaked state between tests (any process scheduled by one test would
# notionally remain in the env's queue forever). Tests now own their env, and
# ``DummyNode`` accepts an ``env=`` parameter so its suppliers / links bind
# to the same env the test creates in ``setUp``.

def _fresh_env() -> simpy.Environment:
    """Convenience factory for per-test SimPy environments (§7 isolation)."""
    return simpy.Environment()

# Module-level env retained as a fallback for the (few) places that still
# reference it directly. New tests should call ``_fresh_env()`` in setUp.
env = _fresh_env()

class TestRawMaterial(unittest.TestCase):
    """
    Testing RawMaterial.

    The fixture is built in :meth:`setUp` (instance attribute) rather than at
    class-construction time. The previous class-attribute version triggered
    ``RawMaterial(...)`` at import time, so an unrelated import-time
    regression surfaced as a *collection error* (no test name in the failure
    line) instead of a clean test failure (§7).
    """

    def setUp(self):
        self.raw_material = scm.RawMaterial(ID="RM1",
                                            name="Raw Material 1",
                                            extraction_quantity=30,
                                            extraction_time=3,
                                            mining_cost=4,
                                            cost=1)

    def test_raw_material_init(self):
        assert self.raw_material.ID == "RM1"
        assert self.raw_material.name == "Raw Material 1"
        assert self.raw_material.extraction_quantity == 30
        assert self.raw_material.extraction_time == 3
        assert self.raw_material.mining_cost == 4
        assert self.raw_material.cost == 1

    def test_raw_material_str_repr(self):
        # __str__ and __repr__ should return name if available
        assert str(self.raw_material) == "Raw Material 1"
        assert repr(self.raw_material) == "Raw Material 1"

    def test_raw_material_info_keys(self):
        # Should contain all info keys
        info = self.raw_material.get_info()
        for key in ['ID', 'name', 'extraction_quantity', 'extraction_time', 'mining_cost', 'cost']:
            assert key in info

    def test_raw_material_invalid_extraction_quantity(self):
        # Should raise ValueError for non-positive extraction_quantity
        with pytest.raises(ValueError):
            scm.RawMaterial(ID="RM2", name="RM2", extraction_quantity=0, extraction_time=2, mining_cost=1, cost=1)

    def test_raw_material_invalid_extraction_time(self):
        # Should raise ValueError for non-positive extraction_time
        with pytest.raises(ValueError):
            scm.RawMaterial(ID="RM3", name="RM3", extraction_quantity=10, extraction_time=-1, mining_cost=1, cost=1)

    def test_raw_material_invalid_mining_cost(self):
        # Should raise ValueError for negative mining_cost
        with pytest.raises(ValueError):
            scm.RawMaterial(ID="RM4", name="RM4", extraction_quantity=10, extraction_time=2, mining_cost=-5, cost=1)

    def test_raw_material_invalid_cost(self):
        # Should raise ValueError for negative cost
        with pytest.raises(ValueError):
            scm.RawMaterial(ID="RM5", name="RM5", extraction_quantity=10, extraction_time=2, mining_cost=1, cost=-1)

class TestProduct(unittest.TestCase):
    """
    Testing Product class. Fixture moved to :meth:`setUp` (§7) so any
    import-time regression in ``RawMaterial`` / ``Product`` surfaces as a
    named test failure rather than a pytest collection error.
    """

    def setUp(self):
        self.raw_material1 = scm.RawMaterial(ID="RM1", name="Raw Material 1", extraction_quantity=10, extraction_time=2, mining_cost=1, cost=2)
        self.raw_material2 = scm.RawMaterial(ID="RM2", name="Raw Material 2", extraction_quantity=5, extraction_time=1, mining_cost=0.5, cost=1)

        self.product = scm.Product(
            ID="P1",
            name="Product 1",
            manufacturing_cost=10,
            manufacturing_time=5,
            sell_price=20,
            raw_materials=[(self.raw_material1, 2), (self.raw_material2, 3)],
            batch_size=100,
            buy_price=15
        )

    def test_product_init(self):
        assert self.product.ID == "P1"
        assert self.product.name == "Product 1"
        assert self.product.manufacturing_cost == 10
        assert self.product.manufacturing_time == 5
        assert self.product.sell_price == 20
        assert self.product.buy_price == 15
        assert self.product.batch_size == 100
        assert isinstance(self.product.raw_materials, list)
        assert self.product.raw_materials[0][0].ID == "RM1"
        assert self.product.raw_materials[0][1] == 2
        assert self.product.raw_materials[1][0].ID == "RM2"
        assert self.product.raw_materials[1][1] == 3

    def test_product_str_repr(self):
        assert str(self.product) == "Product 1"
        assert repr(self.product) == "Product 1"

    def test_product_info_keys(self):
        info = self.product.get_info()
        for key in ['ID', 'name', 'manufacturing_cost', 'manufacturing_time', 'sell_price', 'buy_price', 'raw_materials', 'batch_size']:
            assert key in info

    def test_product_invalid_manufacturing_cost(self):
        with pytest.raises(ValueError):
            scm.Product(
                ID="P2",
                name="Product 2",
                manufacturing_cost=-1,
                manufacturing_time=5,
                sell_price=10,
                raw_materials=[],
                batch_size=10
            )

    def test_product_invalid_manufacturing_time(self):
        with pytest.raises(ValueError):
            scm.Product(
                ID="P3",
                name="Product 3",
                manufacturing_cost=5,
                manufacturing_time=0,
                sell_price=10,
                raw_materials=[],
                batch_size=10
            )

    def test_product_invalid_sell_price(self):
        with pytest.raises(ValueError):
            scm.Product(
                ID="P4",
                name="Product 4",
                manufacturing_cost=5,
                manufacturing_time=2,
                sell_price=-10,
                raw_materials=[],
                batch_size=10
            )

    def test_product_invalid_buy_price(self):
        with pytest.raises(ValueError):
            scm.Product(
                ID="P5",
                name="Product 5",
                manufacturing_cost=5,
                manufacturing_time=2,
                sell_price=10,
                raw_materials=[],
                batch_size=10,
                buy_price=-1
            )

    def test_product_invalid_batch_size(self):
        with pytest.raises(ValueError):
            scm.Product(
                ID="P6",
                name="Product 6",
                manufacturing_cost=5,
                manufacturing_time=2,
                sell_price=10,
                raw_materials=[],
                batch_size=0
            )

    def test_product_no_raw_materials(self):
        with pytest.raises(ValueError):
            product = scm.Product(
                ID="P8",
                name="Product 8",
                manufacturing_cost=5,
                manufacturing_time=2,
                sell_price=10,
                raw_materials=[],
                batch_size=10
            )

    def test_product_invalid_raw_materials(self):
        # Should raise ValueError if raw_materials is not a list of (RawMaterial, quantity) tuples
        with pytest.raises(ValueError):
            scm.Product(
                ID="P7",
                name="Product 7",
                manufacturing_cost=5,
                manufacturing_time=2,
                sell_price=10,
                raw_materials=[("not_a_raw_material", 2)],
                batch_size=10
            )
        with pytest.raises(ValueError):
            scm.Product(
                ID="P8",
                name="Product 8",
                manufacturing_cost=5,
                manufacturing_time=2,
                sell_price=10,
                raw_materials=[(self.raw_material1, -2)],
                batch_size=10
            )

class DummyNode(scm.InventoryNode):
    """Reusable harness — accepts ``env=`` so callers (test setUp) can scope
    every supplier / link / inventory to a fresh environment per test (§7)."""

    def __init__(self, env=None):
        if env is None:
            env = _fresh_env()
        self.infinite_sup1 = scm.Supplier(env, ID="dummy_supplier1", name="Dummy Supplier1", node_type="infinite_supplier")
        self.infinite_sup2 = scm.Supplier(env, ID="dummy_supplier2", name="Dummy Supplier2", node_type="infinite_supplier")
        super().__init__(env=env, ID="dummy_node", name="Dummy Node",
                         node_type="warehouse", capacity=20, initial_level=10,
                         inventory_holding_cost=1.0, replenishment_policy=scm.SSReplenishment,
                         policy_param={'s':5,'S':20}, product_sell_price=10, product_buy_price=5)
        self.link1 = scm.Link(env=env, ID="dummy_link", source=self.infinite_sup1, sink=self, lead_time=lambda:2, cost=1)
        self.link2 = scm.Link(env=env, ID="dummy_link2", source=self.infinite_sup2, sink=self, lead_time=lambda:1, cost=2)

class TestSSReplenishment(unittest.TestCase):
    def setUp(self):
        # §7: per-test env passed into DummyNode so its suppliers / links
        # are scoped to ``self.env``. Replaces the previous module-shared env
        # plus post-hoc ``self.node.env = self.env`` patch (which left
        # node.suppliers / node.inventory bound to the module env).
        self.env = _fresh_env()
        self.node = DummyNode(env=self.env)

    def test_init_sets_params(self):
        params = {'s': 5, 'S': 20}
        ss = scm.SSReplenishment(self.env, self.node, params)
        assert ss.params['s'] == 5
        assert ss.params['S'] == 20
        assert hasattr(ss, 'first_review_delay')
        assert hasattr(ss, 'period')

    def test_invalid_params_raise(self):
        # s >= S should raise ValueError
        with pytest.raises(ValueError):
            scm.SSReplenishment(self.env, self.node, {'s': 10, 'S': 5})
        # Missing s or S
        with pytest.raises(KeyError):
            scm.SSReplenishment(self.env, self.node, {'s': 5})

    def test_first_review_delay_and_period(self):
        params = {'s': 5, 'S': 20, 'first_review_delay': 2, 'period': 5}
        ss = scm.SSReplenishment(self.env, self.node, params)
        assert ss.first_review_delay == 2
        assert ss.period == 5

class TestRQReplenishment(unittest.TestCase):
    def setUp(self):
        # §7: per-test env passed into DummyNode so its suppliers / links
        # are scoped to ``self.env``. Replaces the previous module-shared env
        # plus post-hoc ``self.node.env = self.env`` patch (which left
        # node.suppliers / node.inventory bound to the module env).
        self.env = _fresh_env()
        self.node = DummyNode(env=self.env)

    def test_init_sets_params(self):
        params = {'R': 5, 'Q': 10}
        rq = scm.RQReplenishment(self.env, self.node, params)
        assert rq.params['R'] == 5
        assert rq.params['Q'] == 10
        assert hasattr(rq, 'first_review_delay')
        assert hasattr(rq, 'period')

    def test_invalid_params_raise(self):
        # R < 0 or Q <= 0 should raise ValueError
        with pytest.raises(ValueError):
            scm.RQReplenishment(self.env, self.node, {'R': -1, 'Q': 10})
        with pytest.raises(ValueError):
            scm.RQReplenishment(self.env, self.node, {'R': 5, 'Q': 0})
        # Missing R or Q
        with pytest.raises(KeyError):
            scm.RQReplenishment(self.env, self.node, {'R': 5})

    def test_first_review_delay_and_period(self):
        params = {'R': 5, 'Q': 10, 'first_review_delay': 2, 'period': 5}
        rq = scm.RQReplenishment(self.env, self.node, params)
        assert rq.first_review_delay == 2
        assert rq.period == 5

    def test_str_repr(self):
        params = {'R': 5, 'Q': 10}
        rq = scm.RQReplenishment(self.env, self.node, params)
        assert hasattr(rq, '__str__')
        assert hasattr(rq, '__repr__')

class TestPeriodicReplenishment(unittest.TestCase):
    def setUp(self):
        # §7: per-test env passed into DummyNode so its suppliers / links
        # are scoped to ``self.env``. Replaces the previous module-shared env
        # plus post-hoc ``self.node.env = self.env`` patch (which left
        # node.suppliers / node.inventory bound to the module env).
        self.env = _fresh_env()
        self.node = DummyNode(env=self.env)

    def test_init_sets_params(self):
        params = {'T': 5, 'Q': 1}
        pr = scm.PeriodicReplenishment(self.env, self.node, params)
        assert pr.params['T'] == 5
        assert pr.params['Q'] == 1

    def test_invalid_params_raise(self):
        # T <= 0 should raise ValueError
        with pytest.raises(ValueError):
            scm.PeriodicReplenishment(self.env, self.node, {'T': 0, 'Q': 1})
        # Missing T
        with pytest.raises(KeyError):
            scm.PeriodicReplenishment(self.env, self.node, {})

    def test_str_repr(self):
        params = {'T': 5,'Q':10}
        pr = scm.PeriodicReplenishment(self.env, self.node, params)
        assert hasattr(pr, '__str__')
        assert hasattr(pr, '__repr__')

class TestSelectFirst(unittest.TestCase):
    def setUp(self):
        # §7: per-test env passed into DummyNode so its suppliers / links
        # are scoped to ``self.env``. Replaces the previous module-shared env
        # plus post-hoc ``self.node.env = self.env`` patch (which left
        # node.suppliers / node.inventory bound to the module env).
        self.env = _fresh_env()
        self.node = DummyNode(env=self.env)

    def test_init_sets_params(self):
        sf = scm.SelectFirst(self.node, "fixed")
        assert sf.mode == "fixed"

    def test_invalid_params_raise(self):
        with pytest.raises(ValueError):
            scm.SelectFirst(self.node, "other")

    def test_selects_first(self):
        sf = scm.SelectFirst(self.node, "fixed")
        assert sf.select(order_quantity=1) == self.node.suppliers[0]

class TestSelectAvailable(unittest.TestCase):
    def setUp(self):
        # §7: per-test env passed into DummyNode so its suppliers / links
        # are scoped to ``self.env``. Replaces the previous module-shared env
        # plus post-hoc ``self.node.env = self.env`` patch (which left
        # node.suppliers / node.inventory bound to the module env).
        self.env = _fresh_env()
        self.node = DummyNode(env=self.env)

    def test_init_sets_params(self):
        sa = scm.SelectAvailable(self.node, "fixed")
        assert sa.mode == "fixed"

    def test_invalid_params_raise(self):
        with pytest.raises(ValueError):
            scm.SelectAvailable(self.node, "other")

    def test_selects_available(self):
        sa = scm.SelectAvailable(self.node, "fixed")
        assert sa.select(order_quantity=1) == self.node.suppliers[0]
        sa = scm.SelectAvailable(self.node, "dynamic")
        assert sa.select(order_quantity=1) == self.node.suppliers[0]

class TestSelectCheapest(unittest.TestCase):
    def setUp(self):
        # §7: per-test env passed into DummyNode so its suppliers / links
        # are scoped to ``self.env``. Replaces the previous module-shared env
        # plus post-hoc ``self.node.env = self.env`` patch (which left
        # node.suppliers / node.inventory bound to the module env).
        self.env = _fresh_env()
        self.node = DummyNode(env=self.env)

    def test_init_sets_params(self):
        sc = scm.SelectCheapest(self.node, "fixed")
        assert sc.mode == "fixed"

    def test_invalid_params_raise(self):
        with pytest.raises(ValueError):
            scm.SelectCheapest(self.node, "other")

    def test_selects_cheapest(self):
        sc = scm.SelectCheapest(self.node, "fixed")
        assert sc.select(order_quantity=1) == self.node.suppliers[0]
        sc = scm.SelectCheapest(self.node, "dynamic")
        assert sc.select(order_quantity=1) == self.node.suppliers[0]

class TestSelectFastest(unittest.TestCase):
    def setUp(self):
        # §7: per-test env passed into DummyNode so its suppliers / links
        # are scoped to ``self.env``. Replaces the previous module-shared env
        # plus post-hoc ``self.node.env = self.env`` patch (which left
        # node.suppliers / node.inventory bound to the module env).
        self.env = _fresh_env()
        self.node = DummyNode(env=self.env)

    def test_init_sets_params(self):
        sf = scm.SelectFastest(self.node, "fixed")
        assert sf.mode == "fixed"

    def test_invalid_params_raise(self):
        with pytest.raises(ValueError):
            scm.SelectFastest(self.node, "other")

    def test_selects_fastest(self):
        sf = scm.SelectFastest(self.node, "fixed")
        assert sf.select(order_quantity=1) == self.node.suppliers[1]
        sf = scm.SelectFastest(self.node, "dynamic")
        assert sf.select(order_quantity=1) == self.node.suppliers[1]

class TestInventory(unittest.TestCase):
    def setUp(self):
        # §7: per-test env passed into DummyNode so its suppliers / links
        # are scoped to ``self.env``. Replaces the previous module-shared env
        # plus post-hoc ``self.node.env = self.env`` patch (which left
        # node.suppliers / node.inventory bound to the module env).
        self.env = _fresh_env()
        self.node = DummyNode(env=self.env)

    def test_init_sets_params(self):
        inv = scm.Inventory(env=self.node.env, capacity=20, initial_level=10, node=self.node, replenishment_policy=None,
                            holding_cost=0.1)
        assert inv.node == self.node
        assert inv.capacity == 20
        assert inv.init_level == 10
        assert inv.replenishment_policy is None
        assert inv.holding_cost == 0.1

    def test_invalid_capacity_raises(self):
        with pytest.raises(ValueError):
            scm.Inventory(env=self.node.env, capacity=-10, initial_level=10, node=self.node, replenishment_policy=None,
                            holding_cost=0.1)
            
    def test_invalid_initial_level(self):
        with pytest.raises(ValueError):
            scm.Inventory(env=self.node.env, capacity=20, initial_level=-10, node=self.node, replenishment_policy=None,
                            holding_cost=0.1)
            
    def test_invalid_shelf_life(self):
        with pytest.raises(ValueError):
            scm.Inventory(env=self.node.env, capacity=20, initial_level=10, node=self.node, replenishment_policy=None,
                            holding_cost=0.1, shelf_life=-1)
        with pytest.raises(ValueError):
            scm.Inventory(env=self.node.env, capacity=20, initial_level=10, node=self.node, replenishment_policy=None,
                            holding_cost=0.1, shelf_life=0, inv_type="perishable")

    def test_invalid_inv_type(self):
        with pytest.raises(ValueError):
            scm.Inventory(env=self.node.env, capacity=20, initial_level=10, node=self.node, replenishment_policy=None,
                            holding_cost=0.1, shelf_life=10, inv_type="invalid")

    def test_str_repr(self):
        inv = scm.Inventory(env=self.node.env, capacity=20, initial_level=10, node=self.node, replenishment_policy=None,
                            holding_cost=0.1)
        assert hasattr(inv, '__str__')
        assert hasattr(inv, '__repr__')

    def test_inv_methods(self):
        inv = scm.Inventory(env=self.node.env, capacity=20, initial_level=10, node=self.node, replenishment_policy=None,
                            holding_cost=0.1)
        assert callable(inv.get_info)
        assert callable(inv.get_statistics)

class TestSupplier(unittest.TestCase):
    rawmat = scm.RawMaterial(ID="RM1", name="Raw Material 1", extraction_quantity=10, extraction_time=2, mining_cost=1, cost=2)
    def setUp(self):
        self.env = simpy.Environment()
        self.supplier = scm.Supplier(env=self.env, ID="S1", name="Supplier 1", node_type="infinite_supplier")

    def test_init_sets_params(self):
        assert self.supplier.ID == "S1"
        assert self.supplier.name == "Supplier 1"
        assert self.supplier.node_type == "infinite_supplier"

    def test_str_repr(self):
        assert str(self.supplier) == "Supplier 1"
        assert repr(self.supplier) == "Supplier 1"

    def test_info_keys(self):
        info = self.supplier.get_info()
        for key in ['ID', 'name', 'node_type']:
            assert key in info

    def test_invalid_node_type(self):
        with pytest.raises(ValueError):
            scm.Supplier(env=self.env, ID="S2", name="Supplier 2", node_type="invalid_type")

    def test_valid_supplier(self):
        node = scm.Supplier(env=self.env, ID="S2", name="Supplier 2", node_type="supplier", capacity=100, initial_level=50,
                            inventory_holding_cost=0.5, raw_material=self.rawmat)
        assert node.node_type == "supplier"

    def test_supplier_invalid_raw_material(self):
        with pytest.raises(ValueError):
            scm.Supplier(env=self.env, ID="S2", name="Supplier 2", node_type="supplier", capacity=100, initial_level=50,
                          inventory_holding_cost=0.5, raw_material=None)
            
    def test_supplier_invalid_capacity(self):
        with pytest.raises(ValueError):
            scm.Supplier(env=self.env, ID="S2", name="Supplier 2", node_type="supplier", capacity=-100, initial_level=50,
                          inventory_holding_cost=0.5, raw_material=self.rawmat)

    def test_supplier_invalid_initial_level(self):
        with pytest.raises(ValueError):
            scm.Supplier(env=self.env, ID="S2", name="Supplier 2", node_type="supplier", capacity=100, initial_level=-50,
                          inventory_holding_cost=0.5, raw_material=self.rawmat)

    def test_supplier_invalid_inventory_holding_cost(self):
        with pytest.raises(ValueError):
            scm.Supplier(env=self.env, ID="S2", name="Supplier 2", node_type="supplier", capacity=100, initial_level=50,
                          inventory_holding_cost=-0.5, raw_material=self.rawmat)
            
class TestInventoryNode(unittest.TestCase):
    def setUp(self):
        self.env = simpy.Environment()
        self.inventory_node = scm.InventoryNode(env=self.env, ID="IN1", name="Inventory Node 1", capacity=100, initial_level=50,
                                                node_type="warehouse", inventory_holding_cost=0.5, replenishment_policy=None, 
                                                policy_param=None, product_sell_price=10, product_buy_price=5)

    def test_init_sets_params(self):
        assert self.inventory_node.ID == "IN1"
        assert self.inventory_node.name == "Inventory Node 1"
        assert self.inventory_node.sell_price == 10
        assert self.inventory_node.buy_price == 5

    def test_str_repr(self):
        assert str(self.inventory_node) == "Inventory Node 1"
        assert repr(self.inventory_node) == "Inventory Node 1"

    def test_invalid_node_type(self):
        with pytest.raises(ValueError):
            scm.InventoryNode(env=self.env, ID="IN2", name="Inventory Node 2", node_type="unknown", capacity=100, initial_level=50,
                              inventory_holding_cost=0.5, replenishment_policy=None, policy_param=None, 
                              product_sell_price=10, product_buy_price=5)            
    
    def test_invalid_capacity(self):
        with pytest.raises(ValueError):
            scm.InventoryNode(env=self.env, ID="IN2", name="Inventory Node 2", node_type="warehouse", capacity=-100, initial_level=50,
                              inventory_holding_cost=0.5, replenishment_policy=None, policy_param=None, 
                              product_sell_price=10, product_buy_price=5)

    def test_invalid_initial_level(self):
        with pytest.raises(ValueError):
            scm.InventoryNode(env=self.env, ID="IN2", name="Inventory Node 2", node_type="warehouse", capacity=100, initial_level=-50,
                              inventory_holding_cost=0.5, replenishment_policy=None, policy_param=None,
                              product_sell_price=10, product_buy_price=5)

    def test_invalid_inventory_holding_cost(self):
        with pytest.raises(ValueError):
            scm.InventoryNode(env=self.env, ID="IN2", name="Inventory Node 2", node_type="warehouse", capacity=100, initial_level=50,
                              inventory_holding_cost=-0.5, replenishment_policy=None, policy_param=None,
                              product_sell_price=10, product_buy_price=5)
            
    def test_invalid_product_sell_price(self):
        with pytest.raises(ValueError):
            scm.InventoryNode(env=self.env, ID="IN2", name="Inventory Node 2", node_type="warehouse", capacity=100, initial_level=50,
                              inventory_holding_cost=0.5, replenishment_policy=None, policy_param=None,
                              product_sell_price=-10, product_buy_price=5)

    def test_invalid_product_buy_price(self):
        with pytest.raises(ValueError):
            scm.InventoryNode(env=self.env, ID="IN2", name="Inventory Node 2", node_type="warehouse", capacity=100, initial_level=50,
                              inventory_holding_cost=0.5, replenishment_policy=None, policy_param=None,
                              product_sell_price=10, product_buy_price=-5)

class TestManufacturer(unittest.TestCase):
    rawmat = scm.RawMaterial(ID="RM1", name="Raw Material 1", extraction_quantity=5, extraction_time=1, mining_cost=1, cost=5)
    product = scm.Product(ID="P1", name="Product 1", manufacturing_cost=10, manufacturing_time=5,
                          raw_materials=[(rawmat,2)], sell_price=15, buy_price=5, batch_size=30)
    def setUp(self):
        self.env = simpy.Environment()
        self.manufacturer = scm.Manufacturer(env=self.env, ID="M1", name="Manufacturer 1",
                                            capacity=100, initial_level=50, inventory_holding_cost=0.5,
                                            replenishment_policy=None, policy_param=None, product_sell_price=10,
                                            product=self.product)

    def test_init_sets_params(self):
        assert self.manufacturer.ID == "M1"
        assert self.manufacturer.name == "Manufacturer 1"
        assert self.manufacturer.sell_price == 10

    def test_no_product(self):
        with pytest.raises(ValueError):
            scm.Manufacturer(env=self.env, ID="M2", name="Manufacturer 2", capacity=100, initial_level=50,
                             inventory_holding_cost=0.5, replenishment_policy=None, policy_param=None,
                             product_sell_price=10, product=None)
            
    def test_invalid_product(self):
        with pytest.raises(ValueError):
            scm.Manufacturer(env=self.env, ID="M2", name="Manufacturer 2", capacity=100, initial_level=50,
                             inventory_holding_cost=0.5, replenishment_policy=None, policy_param=None,
                             product_sell_price=10, product="Not a Product")
    
    def test_invalid_sell_price(self):
        with pytest.raises(ValueError):
            scm.Manufacturer(env=self.env, ID="M2", name="Manufacturer 2", capacity=100, initial_level=50,
                             inventory_holding_cost=0.5, replenishment_policy=None, policy_param=None,
                             product_sell_price=-10, product=self.product)
            
class TestDemand(unittest.TestCase):
    def setUp(self):
        self.env = simpy.Environment()
        self.node = scm.InventoryNode(env=self.env, ID="IN1", name="Inventory Node 1", capacity=100, initial_level=50,
                                      node_type="warehouse", inventory_holding_cost=0.5, replenishment_policy=None, 
                                      policy_param=None, product_sell_price=10, product_buy_price=5)
        self.demand = scm.Demand(env=self.env, ID="d1", name="Demand 1", order_arrival_model=lambda:1, order_quantity_model=lambda:10,
                                 demand_node=self.node)

    def test_str_repr(self):
        assert str(self.demand) == "Demand 1"
        assert repr(self.demand) == "Demand 1"

    def test_no_env(self):
        with pytest.raises(ValueError):
            scm.Demand(env=None, ID="d2", name="Demand 2", order_arrival_model=lambda:1, order_quantity_model=lambda:10,
                       demand_node=self.node)

    def test_no_demand_node(self):
        with pytest.raises(ValueError):
            scm.Demand(env=self.env, ID="d2", name="Demand 2", order_arrival_model=lambda:1, order_quantity_model=lambda:10,
                       demand_node=None)

    def test_invalid_order_arrival_model(self):
        with pytest.raises(ValueError):
            scm.Demand(env=self.env, ID="d2", name="Demand 2", order_arrival_model="Not a function", order_quantity_model=lambda:10,
                       demand_node=self.node)
    
    def test_invalid_order_quantity_model(self):
        with pytest.raises(ValueError):
            scm.Demand(env=self.env, ID="d2", name="Demand 2", order_arrival_model=lambda:1, order_quantity_model="Not a function",
                       demand_node=self.node)

class TestNode(unittest.TestCase):
    def setUp(self):
        self.env = simpy.Environment()
        self.node = scm.Node(env=self.env, ID="N1", name="Inventory Node 1", node_type="warehouse")

    def test_str_repr(self):
        assert str(self.node) == "Inventory Node 1"
        assert repr(self.node) == "Inventory Node 1"

    def test_no_env(self):
        with pytest.raises(ValueError):
            scm.Node(env=None, ID="N1", name="Inventory Node 1", node_type="warehouse")

    def test_invalid_node_type(self):
        with pytest.raises(ValueError):
            scm.Node(env=self.env, ID="N2", name="Inventory Node 2", node_type="invalid_type")

class TestLink(unittest.TestCase):
    env = simpy.Environment()
    node1 = scm.InventoryNode(env=env, ID="N1", name="Node 1", node_type="supplier", capacity=100, initial_level=50,
                              inventory_holding_cost=0.5, replenishment_policy=None, policy_param=None, product_sell_price=10, product_buy_price=5)
    node2 = scm.InventoryNode(env=env, ID="N2", name="Node 2", node_type="warehouse", capacity=100, initial_level=50,
                              inventory_holding_cost=0.5, replenishment_policy=None, policy_param=None, product_sell_price=10, product_buy_price=5)

    def setUp(self):
        self.link = scm.Link(env=self.env, ID="l1", source=self.node1, sink=self.node2, lead_time=lambda: 1, cost=5)

    def test_init_sets_params(self):
        assert self.link.env == self.env
        assert self.link.ID == "l1"
        assert self.link.source == self.node1
        assert self.link.sink == self.node2
        assert self.link.lead_time() == 1
        assert self.link.cost == 5

    def test_invalid_env(self):
        with pytest.raises(ValueError):
            scm.Link(env=None, ID="l2", source=self.node1, sink=self.node2, lead_time=lambda: 1, cost=5)
        with pytest.raises(ValueError):
            scm.Link(env="not a simpy Environment", ID="l2", source=self.node1, sink=self.node2, lead_time=lambda: 1, cost=5)
    
    def test_invalid_source(self):
        with pytest.raises(ValueError):
            scm.Link(env=self.env, ID="l2", source=None, sink=self.node2, lead_time=lambda: 1, cost=5)
        with pytest.raises(ValueError):
            scm.Link(env=self.env, ID="l2", source="not of type Node", sink=self.node2, lead_time=lambda: 1, cost=5)    

    def test_invalid_sink(self):
        with pytest.raises(ValueError):
            scm.Link(env=self.env, ID="l2", source=self.node1, sink=None, lead_time=lambda: 1, cost=5)
        with pytest.raises(ValueError):
            scm.Link(env=self.env, ID="l2", source=self.node1, sink="not of type Node", lead_time=lambda: 1, cost=5)

    def test_invalid_lead_time(self):
        with pytest.raises(ValueError):
            scm.Link(env=self.env, ID="l2", source=self.node1, sink=self.node2, lead_time="not a function", cost=5)
        with pytest.raises(ValueError):
            scm.Link(env=self.env, ID="l3", source=self.node1, sink=self.node2, lead_time=None, cost=5)


# ---------------------------------------------------------------------------
# Invariant tests for the §3 correctness fixes in REVIEW.md.
# These lock in the contracts established while resolving REVIEW §3.1–§3.13 so
# future refactors (especially §4.1's core.py split) can't silently regress.
# ---------------------------------------------------------------------------


_HARNESS_COUNTER = [0]


def _make_inventory(env, capacity=100, initial_level=50, inv_type="non-perishable", **kwargs):
    """Construct an Inventory wired into a fresh InventoryNode harness.

    An InventoryNode owner is required because Inventory.put/get reach into
    node.inventory_raised / node.inventory_drop (simpy events that only exist on
    nodes that actually participate in replenishment). A plain infinite Supplier
    does not create those events.
    """
    _HARNESS_COUNTER[0] += 1
    harness_id = f"_H{_HARNESS_COUNTER[0]}"
    node = scm.InventoryNode(env=env, ID=harness_id, name=harness_id,
                             node_type="warehouse", capacity=capacity,
                             initial_level=initial_level,
                             inventory_holding_cost=0.1,
                             replenishment_policy=None, policy_param=None,
                             product_sell_price=1, product_buy_price=1,
                             inventory_type=inv_type, logging=False,
                             **{k: v for k, v in kwargs.items() if k != "replenishment_policy"})
    # The node builds its own Inventory internally; return that one so tests
    # observe the same object the node owns.
    inv = node.inventory
    inv.holding_cost = 0.1
    return inv


class TestInventoryPutContract(unittest.TestCase):
    """§3.6: Inventory.put returns the accepted amount; callers must reconcile."""

    def setUp(self):
        self.env = simpy.Environment()

    def test_put_returns_accepted_when_fits(self):
        inv = _make_inventory(self.env, capacity=100, initial_level=50)
        accepted = inv.put(30)
        assert accepted == 30
        assert inv.level == 80

    def test_put_clamps_at_capacity_and_returns_clamped_amount(self):
        inv = _make_inventory(self.env, capacity=100, initial_level=50)
        accepted = inv.put(80)
        assert accepted == 50  # only 50 units of headroom remained
        assert inv.level == 100

    def test_put_returns_zero_when_already_full(self):
        inv = _make_inventory(self.env, capacity=100, initial_level=100)
        assert inv.put(10) == 0
        assert inv.level == 100

    def test_put_returns_zero_for_non_positive_amount(self):
        inv = _make_inventory(self.env, capacity=100, initial_level=50)
        assert inv.put(0) == 0
        assert inv.put(-5) == 0
        assert inv.level == 50

    def test_put_returns_zero_on_infinite_inventory(self):
        inv = _make_inventory(self.env, capacity=float("inf"), initial_level=float("inf"))
        assert inv.put(100) == 0


class TestInventoryLevelProperty(unittest.TestCase):
    """§3.7: Inventory.level and Inventory.capacity delegate to the SimPy container."""

    def setUp(self):
        self.env = simpy.Environment()
        self.inv = _make_inventory(self.env, capacity=200, initial_level=75)

    def test_level_delegates_to_container(self):
        # Before any operation, level should match the container and the initial level.
        assert self.inv.level == 75
        assert self.inv.level is self.inv.inventory.level or self.inv.level == self.inv.inventory.level

    def test_capacity_delegates_to_container(self):
        assert self.inv.capacity == 200
        assert self.inv.capacity == self.inv.inventory.capacity

    def test_level_is_read_only_property(self):
        with pytest.raises(AttributeError):
            self.inv.level = 999

    def test_level_updates_when_container_mutates(self):
        self.inv.put(25)
        assert self.inv.level == 100  # property reflects live container state
        self.inv.get(40)
        # get returns (event, man_date_ls); the event needs to be yielded in a
        # simpy process for the container to actually drop, but level delegates
        # to container.level so we only assert delegation here.
        # Verify the delegation contract by checking identity of the read path:
        assert self.inv.level == self.inv.inventory.level


class TestInventoryKwargHygiene(unittest.TestCase):
    """§3.3: stray kwargs don't silently vanish into Inventory; logger kwargs stay filtered."""

    def setUp(self):
        self.env = simpy.Environment()

    def test_typo_kwarg_raises_at_inventory_boundary(self):
        # `shelf_live` is a typo for `shelf_life` — must raise, not silently swallow.
        with pytest.raises(TypeError):
            scm.InventoryNode(env=self.env, ID="IN_T", name="T", node_type="warehouse",
                              capacity=50, initial_level=10, inventory_holding_cost=0.1,
                              replenishment_policy=None, policy_param=None,
                              product_sell_price=5, product_buy_price=2, shelf_live=5)

    def test_logger_kwargs_do_not_leak_to_inventory(self):
        # log_to_file / log_to_screen are accepted by Node's logger, not Inventory.
        node = scm.InventoryNode(env=self.env, ID="IN_L", name="L", node_type="warehouse",
                                 capacity=50, initial_level=10, inventory_holding_cost=0.1,
                                 replenishment_policy=None, policy_param=None,
                                 product_sell_price=5, product_buy_price=2,
                                 log_to_file=False, log_to_screen=False)
        assert node.inventory.level == 10  # construction succeeded


class TestInventoryReplenishmentPolicyInstance(unittest.TestCase):
    """§3.8: passing a non-InventoryReplenishment instance raises TypeError, not AttributeError."""

    def setUp(self):
        self.env = simpy.Environment()

    def test_instance_of_wrong_class_raises_type_error(self):
        class NotAPolicy:
            pass
        # Construct an owner node first so Inventory has a logger to route errors through.
        owner = scm.InventoryNode(env=self.env, ID="IN_BAD_POL", name="X", node_type="warehouse",
                                  capacity=10, initial_level=0, inventory_holding_cost=0.1,
                                  replenishment_policy=None, policy_param=None,
                                  product_sell_price=1, product_buy_price=1, logging=False)
        with pytest.raises(TypeError):
            scm.Inventory(env=self.env, capacity=10, initial_level=0, node=owner,
                          replenishment_policy=NotAPolicy(), holding_cost=0.1)


class TestStatisticsCostComposition(unittest.TestCase):
    """§3.4: node_cost is summed from an explicit list, not by substring-matching 'cost'."""

    def setUp(self):
        self.env = simpy.Environment()

    def test_default_inventorynode_cost_components(self):
        node = scm.InventoryNode(env=self.env, ID="IN_C", name="C", node_type="warehouse",
                                 capacity=100, initial_level=50, inventory_holding_cost=0.1,
                                 replenishment_policy=None, policy_param=None,
                                 product_sell_price=5, product_buy_price=2)
        # ``destroyed_value`` joins the cost components so disruption-driven
        # inventory loss (Inventory.destroy + disruption_impact) shows up in
        # node_cost (and therefore profit) without callers needing a
        # separate "loss" line.
        expected = {"inventory_carry_cost", "inventory_spend_cost", "transportation_cost", "destroyed_value"}
        assert expected == set(node.stats._cost_components)

    def test_supplier_adds_material_cost_component(self):
        rm = scm.RawMaterial(ID="RM_X", name="rm", extraction_quantity=5,
                             extraction_time=1, mining_cost=1, cost=2)
        s = scm.Supplier(env=self.env, ID="S_C", name="S", node_type="supplier",
                         capacity=10, initial_level=5, inventory_holding_cost=0.1,
                         raw_material=rm)
        assert "total_material_cost" in s.stats._cost_components

    def test_stray_cost_attribute_does_not_inflate_node_cost(self):
        # Attributes whose names contain "cost" but aren't in _cost_components
        # must not be summed into node_cost (old reflection-based implementation
        # would pick them up by substring match).
        node = scm.InventoryNode(env=self.env, ID="IN_S", name="S", node_type="warehouse",
                                 capacity=100, initial_level=50, inventory_holding_cost=0.1,
                                 replenishment_policy=None, policy_param=None,
                                 product_sell_price=5, product_buy_price=2)
        node.stats.random_cost_metric = 999999  # decoy — must be ignored
        node.stats.update_stats()
        assert node.stats.node_cost < 999999  # decoy did not leak into the sum


class TestRNGControl(unittest.TestCase):
    """§3.9: set_seed is reproducible; explicit rng= injection works; default falls back to _rng."""

    def setUp(self):
        # _rng starts with _ so it's excluded from the wildcard re-export;
        # reach it through the core module directly.
        from SupplyNetPy.Components import core as _core
        self.core = _core

    def test_set_seed_reproducible(self):
        scm.set_seed(42)
        a = [self.core._rng.random() for _ in range(5)]
        scm.set_seed(42)
        b = [self.core._rng.random() for _ in range(5)]
        assert a == b

    def test_set_seed_differs_across_seeds(self):
        scm.set_seed(42)
        a = [self.core._rng.random() for _ in range(5)]
        scm.set_seed(7)
        c = [self.core._rng.random() for _ in range(5)]
        assert a != c

    def test_explicit_rng_attached(self):
        env = simpy.Environment()
        my_rng = random.Random(99)
        node = scm.Supplier(env=env, ID="S_RNG1", name="S", node_type="infinite_supplier",
                            rng=my_rng, logging=False)
        assert node.rng is my_rng

    def test_default_rng_fallback_to_library_default(self):
        env = simpy.Environment()
        node = scm.Supplier(env=env, ID="S_RNG2", name="S", node_type="infinite_supplier",
                            logging=False)
        assert node.rng is self.core._rng

    def test_rng_kwarg_does_not_leak_to_inventory(self):
        # rng is a Node-level kwarg; the inventory_kwargs filter in Supplier /
        # InventoryNode / Manufacturer must strip it before forwarding to Inventory.
        env = simpy.Environment()
        rm = scm.RawMaterial(ID="RM_R", name="r", extraction_quantity=5,
                             extraction_time=1, mining_cost=1, cost=2)
        node = scm.Supplier(env=env, ID="S_RNG3", name="S", node_type="supplier",
                            capacity=10, initial_level=5, inventory_holding_cost=0.1,
                            raw_material=rm, rng=random.Random(1), logging=False)
        assert node.inventory.level == 5  # construction succeeded through the filter


class TestPendingOrdersCounter(unittest.TestCase):
    """§3.12: pending_orders is an int counter; no `ongoing_order` bool attribute."""

    def setUp(self):
        self.env = simpy.Environment()

    def test_inventorynode_starts_with_zero_pending(self):
        node = scm.InventoryNode(env=self.env, ID="IN_P", name="P", node_type="warehouse",
                                 capacity=100, initial_level=50, inventory_holding_cost=0.1,
                                 replenishment_policy=None, policy_param=None,
                                 product_sell_price=5, product_buy_price=2)
        assert node.pending_orders == 0
        assert not hasattr(node, "ongoing_order")

    def test_pending_orders_in_get_info(self):
        node = scm.InventoryNode(env=self.env, ID="IN_PI", name="PI", node_type="warehouse",
                                 capacity=100, initial_level=50, inventory_holding_cost=0.1,
                                 replenishment_policy=None, policy_param=None,
                                 product_sell_price=5, product_buy_price=2)
        assert "pending_orders" in node.get_info()

    def test_counter_tracks_in_flight_orders_end_to_end(self):
        # Build the intro_simple scenario; at t=20 exactly one order is in transit
        # (dispatched at t=19, lead_time=2) per the canonical trace.
        import SupplyNetPy.Components.utilities as util
        sc = util.create_sc_net(
            nodes=[{"ID": "S1", "name": "S", "node_type": "infinite_supplier"},
                   {"ID": "D1", "name": "D", "node_type": "distributor",
                    "capacity": 150, "initial_level": 50, "inventory_holding_cost": 0.2,
                    "replenishment_policy": scm.SSReplenishment,
                    "policy_param": {"s": 100, "S": 150},
                    "product_buy_price": 100, "product_sell_price": 105}],
            links=[{"ID": "L1", "source": "S1", "sink": "D1", "cost": 5, "lead_time": lambda: 2}],
            demands=[{"ID": "d1", "name": "d", "order_arrival_model": lambda: 1,
                      "order_quantity_model": lambda: 10, "demand_node": "D1"}])
        util.simulate_sc_net(sc, sim_time=20, logging=False)
        assert sc["nodes"]["D1"].pending_orders == 1


class TestBackorderAwareCapacityClamp(unittest.TestCase):
    """§3.10: process_order's capacity pre-check subtracts customer backorders from on_hand."""

    def test_gross_formula_matches_policy_view(self):
        # We can't easily race the policy tick, but we can verify that when
        # backorder[1] > 0 and on_hand is at capacity, reorder_quantity would NOT
        # be clamped to zero by the pre-check — i.e. the formula uses gross, not raw on_hand.
        # This is a static documentation-test of the exact expression used in process_order.
        import inspect
        src = inspect.getsource(scm.InventoryNode.process_order)
        assert "self.inventory.on_hand - self.stats.backorder[1]" in src, \
            "§3.10 capacity clamp must subtract backorder[1] from on_hand"
        src2 = inspect.getsource(scm.Manufacturer.process_order)
        assert "self.inventory.on_hand - self.stats.backorder[1]" in src2, \
            "§3.10 capacity clamp in Manufacturer must also subtract backorder[1]"


class TestCanonicalIntroSimple(unittest.TestCase):
    """Locks the canonical intro_simple.py scenario output.

    Any change to the simulation semantics that shifts these numbers will fail
    this test. Keep in sync with examples/py/intro_simple.py.
    """

    def test_canonical_end_state(self):
        import SupplyNetPy.Components.utilities as util
        sc = util.create_sc_net(
            nodes=[{"ID": "S1", "name": "Supplier1", "node_type": "infinite_supplier"},
                   {"ID": "D1", "name": "Distributor1", "node_type": "distributor",
                    "capacity": 150, "initial_level": 50, "inventory_holding_cost": 0.2,
                    "replenishment_policy": scm.SSReplenishment,
                    "policy_param": {"s": 100, "S": 150},
                    "product_buy_price": 100, "product_sell_price": 105}],
            links=[{"ID": "L1", "source": "S1", "sink": "D1", "cost": 5, "lead_time": lambda: 2}],
            demands=[{"ID": "d1", "name": "Demand1", "order_arrival_model": lambda: 1,
                      "order_quantity_model": lambda: 10, "demand_node": "D1"}])
        util.simulate_sc_net(sc, sim_time=20, logging=False)

        stats = sc["nodes"]["D1"].stats.get_statistics()
        assert stats["profit"] == -4435.0
        assert stats["revenue"] == 21000
        assert stats["node_cost"] == 25435.0
        assert stats["inventory_level"] == 100
        assert stats["inventory_carry_cost"] == 410.0
        assert stats["inventory_spend_cost"] == 25000
        assert stats["transportation_cost"] == 25
        assert stats["demand_received"] == [20, 200]
        assert stats["demand_fulfilled"] == [20, 200]
        assert stats["shortage"] == [0, 0]
        assert stats["backorder"] == [0, 0]


class TestLinkDisruptionBlocksNewOrders(unittest.TestCase):
    """Link disruption must block *new* replenishment dispatches on that link.

    The scenario: a distributor with s=100, S=150, initial_level=50 would normally
    place a reorder at t=0 via L1. With L1 forced inactive from t=0, that first
    order must be blocked — no demand_placed on D1, no transportation cost, and
    pending_orders stays 0 (blocked orders are not counted as in-flight).
    After L1 recovers, the next policy trigger should succeed, so demand_placed
    crosses from 0 → 1 at that point. Ongoing shipments already dispatched over
    an active link before disruption must not be interrupted.
    """

    def test_new_order_blocked_while_link_inactive(self):
        env = simpy.Environment()
        sup = scm.Supplier(env=env, ID="S1", name="S", node_type="infinite_supplier")
        dist = scm.InventoryNode(env=env, ID="D1", name="D", node_type="distributor",
                                 capacity=150, initial_level=50, inventory_holding_cost=0.2,
                                 replenishment_policy=scm.SSReplenishment,
                                 policy_param={"s": 100, "S": 150},
                                 product_buy_price=100, product_sell_price=105)
        # Construct the link without disruption plumbing, then flip status manually.
        # Link.disruption is only scheduled when link_failure_p>0 or link_disrupt_time
        # is set, so without them nothing in the simulation will re-activate the link.
        link = scm.Link(env=env, ID="L1", source=sup, sink=dist, cost=5, lead_time=lambda: 2)
        link.status = "inactive"
        scm.Demand(env=env, ID="d1", name="d", order_arrival_model=lambda: 1,
                   order_quantity_model=lambda: 10, demand_node=dist)

        env.run(until=5)

        assert link.status == "inactive", "link should stay inactive for the run"
        # No order ever made it to the wire: no transportation cost, no demand_placed,
        # no pending order counted.
        assert dist.stats.demand_placed == [0, 0]
        assert dist.stats.transportation_cost == 0
        assert dist.pending_orders == 0

    def test_ongoing_shipment_unaffected_by_later_disruption(self):
        # Dispatch first, then take the link down. The in-flight order should
        # still complete — disruption only blocks *new* dispatches.
        import SupplyNetPy.Components.utilities as util
        env = simpy.Environment()
        sup = scm.Supplier(env=env, ID="S1", name="S", node_type="infinite_supplier")
        dist = scm.InventoryNode(env=env, ID="D1", name="D", node_type="distributor",
                                 capacity=150, initial_level=50, inventory_holding_cost=0.2,
                                 replenishment_policy=scm.SSReplenishment,
                                 policy_param={"s": 100, "S": 150},
                                 product_buy_price=100, product_sell_price=105)
        # Disrupt_time > lead_time (2) so the first order clears before the link dies.
        link = scm.Link(env=env, ID="L1", source=sup, sink=dist, cost=5,
                        lead_time=lambda: 2, link_disrupt_time=lambda: 3,
                        link_recovery_time=lambda: 10_000)
        scm.Demand(env=env, ID="d1", name="d", order_arrival_model=lambda: 1,
                   order_quantity_model=lambda: 10, demand_node=dist)

        env.run(until=10)

        assert link.status == "inactive", "link should be down after t=3"
        # Exactly one order was in flight when the link went down, and it still
        # completed: fulfillment_received[0] == 1, and the inventory_spend_cost
        # reflects that single 100-unit reorder at buy_price=100.
        assert dist.stats.fulfillment_received[0] == 1
        assert dist.stats.inventory_spend_cost == 100 * 100


class TestSelectionPoliciesFilterDisruptedLinks(unittest.TestCase):
    """Each selection policy must skip disrupted links when picking a supplier.

    Scenarios are built with two suppliers connected via two links. One link is
    flipped to ``inactive`` (without scheduling a Link.disruption process, so
    nothing toggles it back). The policy must return the active link even
    when the disrupted link would otherwise be the "winner" on its own
    criterion (cheapest cost, fastest lead time, first in list, first with
    enough inventory).
    """

    def _build_network(self, cost_a=10, cost_b=5, lead_a=2, lead_b=5,
                       inv_a=100, inv_b=100):
        # Use infinite_supplier nodes with a post-hoc inventory override so each
        # test can control upstream inventory level without Supplier's mining-process
        # plumbing. We only call policy.select() directly (never dispatch), so the
        # supplier inventory just needs a ``.level`` attribute SelectAvailable reads.
        env = simpy.Environment()
        sup_a = scm.Supplier(env=env, ID="SA", name="A", node_type="infinite_supplier")
        sup_b = scm.Supplier(env=env, ID="SB", name="B", node_type="infinite_supplier")
        # Override inventory level for SelectAvailable's inventory-threshold check.
        # infinite_supplier's inventory.level is float('inf') by default; we need
        # bounded values to exercise the "not enough inventory" fallback path.
        sup_a.inventory = simpy.Container(env, capacity=10_000, init=inv_a)
        sup_b.inventory = simpy.Container(env, capacity=10_000, init=inv_b)
        dist = scm.InventoryNode(env=env, ID="D1", name="D", node_type="distributor",
                                 capacity=500, initial_level=0, inventory_holding_cost=0.1,
                                 replenishment_policy=None, policy_param=None,
                                 product_buy_price=50, product_sell_price=60)
        link_a = scm.Link(env=env, ID="LA", source=sup_a, sink=dist, cost=cost_a, lead_time=lambda: lead_a)
        link_b = scm.Link(env=env, ID="LB", source=sup_b, sink=dist, cost=cost_b, lead_time=lambda: lead_b)
        return dist, link_a, link_b

    def test_select_first_skips_disrupted(self):
        dist, link_a, link_b = self._build_network()
        # link_a is first; disrupt it and SelectFirst should pick link_b.
        link_a.status = "inactive"
        policy = scm.SelectFirst(dist, mode="dynamic")
        assert policy.select(10) is link_b

    def test_select_available_skips_disrupted_even_if_it_has_inventory(self):
        dist, link_a, link_b = self._build_network(inv_a=500, inv_b=50)
        # link_a has more inventory, but is disrupted; policy should fall back
        # to link_b which is active even though its inventory (50) can't cover
        # order_quantity (100) — filter runs first, inventory preference second.
        link_a.status = "inactive"
        policy = scm.SelectAvailable(dist, mode="dynamic")
        assert policy.select(100) is link_b

    def test_select_cheapest_skips_disrupted_cheapest(self):
        dist, link_a, link_b = self._build_network(cost_a=10, cost_b=5)
        # link_b is cheaper but disrupted; should pick link_a.
        link_b.status = "inactive"
        policy = scm.SelectCheapest(dist, mode="dynamic")
        assert policy.select(10) is link_a

    def test_select_fastest_skips_disrupted_fastest(self):
        dist, link_a, link_b = self._build_network(lead_a=2, lead_b=1)
        # link_b is faster but disrupted; should pick link_a.
        link_b.status = "inactive"
        policy = scm.SelectFastest(dist, mode="dynamic")
        assert policy.select(10) is link_a

    def test_all_disrupted_falls_back_to_full_list(self):
        # Dispatch gate handles the block, so the policy is allowed to return
        # a disrupted link when there is no active alternative. It must still
        # return *something* (not None) so callers don't need to handle None.
        dist, link_a, link_b = self._build_network(cost_a=10, cost_b=5)
        link_a.status = "inactive"
        link_b.status = "inactive"
        policy = scm.SelectCheapest(dist, mode="dynamic")
        result = policy.select(10)
        assert result in (link_a, link_b)

    def test_fixed_mode_routes_around_disrupted_lock_without_changing_lock(self):
        # First call locks to link_b (cheaper). Then link_b goes down — the
        # policy must return link_a on that call but keep link_b as the lock,
        # so that when link_b recovers it resumes routing through it.
        dist, link_a, link_b = self._build_network(cost_a=10, cost_b=5)
        policy = scm.SelectCheapest(dist, mode="fixed")
        first = policy.select(10)
        assert first is link_b
        assert policy.fixed_supplier is link_b

        link_b.status = "inactive"
        reroute = policy.select(10)
        assert reroute is link_a, "should route around disrupted lock"
        assert policy.fixed_supplier is link_b, "lock must not change"

        link_b.status = "active"
        assert policy.select(10) is link_b, "lock restored once link recovers"


class TestDeclarativeInfoKeys(unittest.TestCase):
    """§4.6: _info_keys / _stats_keys are declared at class level, with subclass lists
    computed as ``Parent._info_keys + [...]`` so they stay in lockstep with the code
    without needing manual ``self._info_keys.extend(...)`` calls in ``__init__``."""

    def test_node_subclass_keys_are_class_level(self):
        # Keys must be readable without constructing any instance.
        assert "raw_material" in scm.Supplier._info_keys
        assert "sell_price" in scm.Supplier._info_keys
        assert "pending_orders" in scm.InventoryNode._info_keys
        assert "selection_policy" in scm.InventoryNode._info_keys
        assert "replenishment_policy" in scm.Manufacturer._info_keys
        assert "order_arrival_model" in scm.Demand._info_keys

    def test_subclass_list_is_independent_of_parent(self):
        # Each subclass must own a fresh list, not alias the parent's — otherwise
        # extending one would pollute the other.
        assert scm.Supplier._info_keys is not scm.Node._info_keys
        assert scm.InventoryNode._info_keys is not scm.Node._info_keys
        assert scm.Manufacturer._info_keys is not scm.Node._info_keys
        assert scm.Demand._info_keys is not scm.Node._info_keys
        assert scm.SSReplenishment._info_keys is not scm.InventoryReplenishment._info_keys
        assert scm.SelectAvailable._info_keys is not scm.SupplierSelectionPolicy._info_keys

    def test_selection_policy_subclass_keys(self):
        assert scm.SelectFirst._info_keys == ["node", "mode", "name"]
        assert scm.SelectAvailable._info_keys == ["node", "mode", "name"]
        assert scm.SelectCheapest._info_keys == ["node", "mode", "name"]
        assert scm.SelectFastest._info_keys == ["node", "mode", "name"]

    def test_get_info_uses_class_level_keys(self):
        env = simpy.Environment()
        rm = scm.RawMaterial(ID="RM", name="rm", extraction_quantity=5,
                             extraction_time=1, mining_cost=1, cost=2)
        sup = scm.Supplier(env=env, ID="S", name="S", node_type="supplier",
                           capacity=10, initial_level=5, inventory_holding_cost=0.1,
                           raw_material=rm, logging=False)
        info = sup.get_info()
        # All Node keys + Supplier extensions.
        for key in ("ID", "name", "node_type", "raw_material", "sell_price"):
            assert key in info

    def test_statistics_per_instance_extension_does_not_leak(self):
        # Supplier.__init__ appends "total_material_cost" to its own stats only.
        # Class-level Statistics._stats_keys must not pick up that append, and
        # sibling Statistics instances (e.g. an InventoryNode's) must not see it
        # either — the instance lists are cloned on construction.
        env = simpy.Environment()
        rm = scm.RawMaterial(ID="RM2", name="rm", extraction_quantity=5,
                             extraction_time=1, mining_cost=1, cost=2)
        sup = scm.Supplier(env=env, ID="SS", name="SS", node_type="supplier",
                           capacity=10, initial_level=5, inventory_holding_cost=0.1,
                           raw_material=rm, logging=False)
        dist = scm.InventoryNode(env=env, ID="DD", name="DD", node_type="distributor",
                                 capacity=100, initial_level=50, inventory_holding_cost=0.1,
                                 replenishment_policy=None, policy_param=None,
                                 product_sell_price=5, product_buy_price=2, logging=False)
        assert "total_material_cost" in sup.stats._stats_keys
        assert "total_material_cost" not in dist.stats._stats_keys
        assert "total_material_cost" not in scm.Statistics._stats_keys
        assert "total_material_cost" in sup.stats._cost_components
        assert "total_material_cost" not in dist.stats._cost_components
        assert "total_material_cost" not in scm.Statistics._cost_components


class TestNodeTypeEnum(unittest.TestCase):
    """§4.7: node_type is validated against the ``NodeType`` str-enum instead of a
    hard-coded list duplicated between ``Node.__init__`` and ``create_sc_net``."""

    def test_enum_members_cover_all_types(self):
        expected = {
            "infinite_supplier", "supplier",
            "manufacturer", "factory",
            "warehouse", "distributor",
            "retailer", "store", "shop",
            "demand",
        }
        assert {m.value for m in scm.NodeType} == expected

    def test_enum_is_str_compatible(self):
        # str-enum inheritance — every comparison the rest of core.py does
        # against a literal string keeps working.
        assert scm.NodeType.SUPPLIER == "supplier"
        assert "supplier" in scm.NodeType.INFINITE_SUPPLIER
        assert scm.NodeType.DEMAND.lower() == "demand"

    def test_case_insensitive_lookup(self):
        assert scm.NodeType("SUPPLIER") is scm.NodeType.SUPPLIER
        assert scm.NodeType("Supplier") is scm.NodeType.SUPPLIER

    def test_node_accepts_enum_or_string(self):
        env = simpy.Environment()
        a = scm.Supplier(env=env, ID="A", name="A", node_type="supplier",
                         capacity=10, initial_level=5, inventory_holding_cost=0.1,
                         raw_material=scm.RawMaterial(ID="rm", name="rm",
                                                      extraction_quantity=1, extraction_time=1,
                                                      mining_cost=1, cost=1),
                         logging=False)
        b = scm.Supplier(env=env, ID="B", name="B", node_type=scm.NodeType.SUPPLIER,
                         capacity=10, initial_level=5, inventory_holding_cost=0.1,
                         raw_material=scm.RawMaterial(ID="rm2", name="rm2",
                                                      extraction_quantity=1, extraction_time=1,
                                                      mining_cost=1, cost=1),
                         logging=False)
        assert a.node_type == b.node_type == "supplier"

    def test_invalid_node_type_raises(self):
        with pytest.raises(ValueError, match="Invalid node type"):
            scm.Node(env=simpy.Environment(), ID="X", name="X",
                     node_type="crossdock", logging=False)


class TestLoggerOptIn(unittest.TestCase):
    """§4.8: ``GlobalLogger`` is inert by default — no FileHandler at import,
    no per-node FileHandlers at construction, and per-node loggers route
    through the single ``sim_trace`` parent so handlers are configured in
    one place."""

    def _file_handlers(self, logger):
        import logging
        return [h for h in logger.handlers if isinstance(h, logging.FileHandler)]

    def test_module_logger_is_inert_by_default(self):
        # After construction the global logger should hold only a NullHandler;
        # specifically no FileHandler should have been opened against the
        # default trace file path.
        import logging
        # Re-create to pick up the documented default state — other tests in
        # the suite may have flipped enable_logging() on this shared logger.
        scm.global_logger.disable_logging()
        assert scm.global_logger.log_to_file is False
        assert scm.global_logger.log_to_screen is False
        assert self._file_handlers(scm.global_logger.logger) == []
        assert any(isinstance(h, logging.NullHandler)
                   for h in scm.global_logger.logger.handlers)

    def test_node_does_not_attach_its_own_file_handler(self):
        # Per-node loggers must not open FileHandlers — they propagate to
        # ``sim_trace`` instead. Construct a node with logging=True (the
        # default) and confirm its logger has no FileHandler of its own.
        env = simpy.Environment()
        node = scm.InventoryNode(env=env, ID="OPTIN_N1", name="N1",
                                 node_type="warehouse", capacity=10,
                                 initial_level=0, inventory_holding_cost=0.1,
                                 replenishment_policy=None, policy_param=None,
                                 product_sell_price=1, product_buy_price=1)
        assert self._file_handlers(node.logger.logger) == []

    def test_per_node_logger_is_child_of_sim_trace(self):
        env = simpy.Environment()
        node = scm.InventoryNode(env=env, ID="OPTIN_N2", name="N2",
                                 node_type="warehouse", capacity=10,
                                 initial_level=0, inventory_holding_cost=0.1,
                                 replenishment_policy=None, policy_param=None,
                                 product_sell_price=1, product_buy_price=1)
        # Hierarchical name → propagation → handlers attached on ``sim_trace``
        # apply to every node without per-node FileHandler creation.
        assert node.logger.logger.name == "sim_trace.OPTIN_N2"

    def test_disable_logging_does_not_set_global_disable(self):
        # The previous implementation called ``logging.disable(CRITICAL)``,
        # silencing the host application's own loggers as a side effect.
        # ``disable_logging`` must be local to ``self.logger`` now.
        import logging
        scm.global_logger.disable_logging()
        # Python tracks the global disable threshold via ``logging.root.manager.disable``.
        assert logging.root.manager.disable == 0
        scm.global_logger.enable_logging()  # restore for any subsequent tests


class TestLoggerAdapter(unittest.TestCase):
    """§4.9: ``GlobalLogger`` is a proper :class:`logging.LoggerAdapter` so
    callers can use ``node.logger.info(...)`` directly — no more
    ``node.logger.logger.info(...)`` double-hop."""

    def test_global_logger_is_a_logger_adapter(self):
        import logging
        assert isinstance(scm.global_logger, logging.LoggerAdapter)

    def test_node_logger_is_a_logger_adapter(self):
        import logging
        env = simpy.Environment()
        node = scm.InventoryNode(env=env, ID="ADAPTER_N1", name="N1",
                                 node_type="warehouse", capacity=10,
                                 initial_level=0, inventory_holding_cost=0.1,
                                 replenishment_policy=None, policy_param=None,
                                 product_sell_price=1, product_buy_price=1,
                                 logging=False)
        assert isinstance(node.logger, logging.LoggerAdapter)
        # All the standard log-level methods route through the adapter directly.
        for method_name in ("debug", "info", "warning", "error", "critical", "log"):
            assert callable(getattr(node.logger, method_name))

    def test_underlying_logger_still_reachable(self):
        # Backward compatibility: ``node.logger.logger`` is the standard
        # LoggerAdapter attribute pointing at the underlying logger. Tests in
        # this file (and any user code that still reaches in) keep working.
        import logging
        env = simpy.Environment()
        node = scm.InventoryNode(env=env, ID="ADAPTER_N2", name="N2",
                                 node_type="warehouse", capacity=10,
                                 initial_level=0, inventory_holding_cost=0.1,
                                 replenishment_policy=None, policy_param=None,
                                 product_sell_price=1, product_buy_price=1,
                                 logging=False)
        assert isinstance(node.logger.logger, logging.Logger)
        assert node.logger.logger.name == "sim_trace.ADAPTER_N2"


class TestPerishQueueHeap(unittest.TestCase):
    """§5.3: ``perish_queue`` is a ``heapq`` min-heap keyed by mfg_date.
    Out-of-order inserts must still be consumed oldest-first, and the heap
    invariant has to survive partial-consumption updates of the head."""

    def setUp(self):
        self.env = simpy.Environment()

    def _heap_invariant_ok(self, heap):
        # For every parent at index i, both children must compare >= parent.
        for i in range(len(heap)):
            for child in (2 * i + 1, 2 * i + 2):
                if child < len(heap):
                    assert heap[i] <= heap[child], (
                        f"Heap invariant broken at i={i}: parent={heap[i]} "
                        f"child={heap[child]}"
                    )

    def test_out_of_order_inserts_consumed_oldest_first(self):
        # Start with a perishable inventory at level 0 (no initial batch), then
        # push three batches with intentionally out-of-order mfg_dates and
        # confirm get() returns them oldest-first.
        inv = _make_inventory(self.env, capacity=100, initial_level=0,
                              inv_type="perishable", shelf_life=100)
        # Drop the (0, 0) sentinel that __init__ seeds for an initial_level=0
        # construction so the test sees only the batches we push below.
        inv.perish_queue.clear()
        inv.put(10, manufacturing_date=5)
        inv.put(10, manufacturing_date=2)   # older — should come out first
        inv.put(10, manufacturing_date=8)
        inv.put(10, manufacturing_date=1)   # oldest of all
        self._heap_invariant_ok(inv.perish_queue)

        _evt, dates = inv.get(40)
        # Order of mfg_dates returned must be ascending — the FIFO-by-expiry
        # contract the heap encodes.
        mfg_dates = [d for d, _ in dates]
        assert mfg_dates == sorted(mfg_dates)
        assert mfg_dates == [1, 2, 5, 8]
        assert inv.perish_queue == []

    def test_partial_consumption_preserves_heap_invariant(self):
        # Consuming less than the head's full qty replaces the head in place.
        # The new tuple has the same mfg_date and a smaller qty; the heap must
        # still satisfy the invariant.
        inv = _make_inventory(self.env, capacity=100, initial_level=0,
                              inv_type="perishable", shelf_life=100)
        inv.perish_queue.clear()
        for d, q in [(5, 30), (2, 20), (8, 40), (1, 10), (3, 25)]:
            inv.put(q, manufacturing_date=d)
        self._heap_invariant_ok(inv.perish_queue)

        # Consume 5 units — only the head (mfg_date=1, qty=10) is touched and
        # gets replaced with (1, 5). The rest of the heap should be intact.
        _evt, dates = inv.get(5)
        assert dates == [(1, 5)]
        assert inv.perish_queue[0] == (1, 5)
        self._heap_invariant_ok(inv.perish_queue)

    def test_remove_expired_drains_oldest_first(self):
        # All batches share the same mfg_date so they all expire together.
        # remove_expired runs as a SimPy process; advance the env past the
        # shelf-life threshold and verify everything is gone.
        inv = _make_inventory(self.env, capacity=100, initial_level=0,
                              inv_type="perishable", shelf_life=3)
        inv.perish_queue.clear()
        for q in (10, 20, 15):
            inv.put(q, manufacturing_date=0)
        self.env.run(until=10)
        assert inv.perish_queue == []
        assert inv.waste == 45  # 10 + 20 + 15


class TestRemoveExpiredEventDriven(unittest.TestCase):
    """§5.1: ``remove_expired`` is event-driven via ``perish_changed``.

    Replaces the old ``yield env.timeout(1)`` polling daemon. The contract:
    the daemon sleeps until the head batch's ``mfg_date + shelf_life`` and
    is woken early only when ``put`` displaces the heap head (or arrives
    into an empty queue). Tests in this class exercise scheduling/wake-up
    semantics; the actual drain-on-expiry behaviour is covered above by
    ``TestPerishQueueHeap.test_remove_expired_drains_oldest_first``.
    """

    def setUp(self):
        self.env = simpy.Environment()

    def test_perish_changed_event_initialised(self):
        inv = _make_inventory(self.env, capacity=100, initial_level=10,
                              inv_type="perishable", shelf_life=5)
        # Should expose an untriggered SimPy event for the daemon wake-up.
        assert hasattr(inv, "perish_changed")
        assert isinstance(inv.perish_changed, simpy.events.Event)
        assert not inv.perish_changed.triggered

    def test_put_into_empty_queue_signals_head_change(self):
        # An empty→non-empty transition is a head change and must wake the
        # daemon. With initial_level=0 the constructor seeds (0, 0); clear it
        # to genuinely simulate "queue currently empty" before the put.
        inv = _make_inventory(self.env, capacity=100, initial_level=0,
                              inv_type="perishable", shelf_life=5)
        inv.perish_queue.clear()
        # Re-arm the wake-up event in case the (0, 0) sentinel push during
        # construction had already triggered it.
        inv.perish_changed = self.env.event()
        inv.put(10, manufacturing_date=2)
        assert inv.perish_changed.triggered

    def test_put_with_younger_batch_does_not_signal(self):
        # In the common (monotonic-mfg_date) case, a fresher batch goes to
        # the back of the heap and the head is unchanged — the daemon must
        # NOT be woken (otherwise §5.1 would still be a per-put wake storm).
        inv = _make_inventory(self.env, capacity=100, initial_level=0,
                              inv_type="perishable", shelf_life=5)
        inv.perish_queue.clear()
        inv.put(10, manufacturing_date=2)
        # Rotate the event so we observe only the next put's effect.
        inv.perish_changed = self.env.event()
        inv.put(10, manufacturing_date=4)  # younger — head stays at mfg_date=2
        assert not inv.perish_changed.triggered
        # And the head is indeed unchanged.
        assert inv.perish_queue[0][0] == 2

    def test_put_with_older_batch_displaces_head_and_signals(self):
        # An older batch (smaller mfg_date) displaces the head: its expiry
        # is earlier than the prior head's, so the daemon's existing timer
        # is too long and it must be woken to recompute.
        inv = _make_inventory(self.env, capacity=100, initial_level=0,
                              inv_type="perishable", shelf_life=5)
        inv.perish_queue.clear()
        inv.put(10, manufacturing_date=4)
        inv.perish_changed = self.env.event()
        inv.put(10, manufacturing_date=1)  # older — becomes new head
        assert inv.perish_changed.triggered
        assert inv.perish_queue[0] == (1, 10)

    def test_daemon_does_not_advance_time_when_queue_empty(self):
        # With initial_level=0 the queue is just the (0, 0) sentinel; after
        # the daemon pops it past shelf_life it should block on
        # perish_changed forever (no spurious timeouts). Run for a long
        # horizon and check the daemon left no expired-batches behind and
        # didn't accumulate phantom waste.
        inv = _make_inventory(self.env, capacity=100, initial_level=0,
                              inv_type="perishable", shelf_life=2)
        # Don't clear perish_queue here — let the daemon process the (0, 0)
        # sentinel naturally. After t >= 2, the sentinel is removed and the
        # daemon should idle, not poll.
        self.env.run(until=1000)
        assert inv.perish_queue == []
        assert inv.waste == 0  # qty=0 sentinel doesn't accrue waste

    def test_late_put_after_idle_wakes_daemon_and_drains_on_schedule(self):
        # Daemon idles on an empty queue, a later put introduces a batch,
        # daemon must wake, sleep shelf_life units, then drain. Verifies the
        # full empty→non-empty→expiry round-trip.
        inv = _make_inventory(self.env, capacity=100, initial_level=0,
                              inv_type="perishable", shelf_life=3)

        def late_put():
            yield self.env.timeout(50)  # daemon has long since idled
            inv.put(20, manufacturing_date=self.env.now)

        self.env.process(late_put())
        # Run past the late put's expiry: 50 + shelf_life = 53. Add slack.
        self.env.run(until=60)
        assert inv.perish_queue == []
        assert inv.waste == 20

    def test_displacing_put_pulls_expiry_earlier(self):
        # Daemon is parked on a long sleep; a stale-mfg_date put arrives and
        # displaces the head with an already-expired batch. Daemon must wake
        # via perish_changed, recompute sleep_dt=0, and drain the stale
        # batch immediately on the next iteration.
        inv = _make_inventory(self.env, capacity=100, initial_level=0,
                              inv_type="perishable", shelf_life=5)
        inv.perish_queue.clear()
        inv.put(10, manufacturing_date=100)  # head: expiry at 105

        def stale_put():
            yield self.env.timeout(10)
            # mfg_date=0 with shelf_life=5 means already expired at t=10.
            inv.put(7, manufacturing_date=0)

        self.env.process(stale_put())
        # Run a hair past the stale put. Daemon should wake at t=10, see
        # sleep_dt=0 on next iteration, and drain the (0, 7) batch.
        self.env.run(until=11)
        # The (0, 7) batch is gone; the (100, 10) batch is still pending.
        mfg_dates_left = [d for d, _ in inv.perish_queue]
        assert 0 not in mfg_dates_left
        assert inv.waste == 7

    def test_fractional_shelf_life_does_not_hang(self):
        # Regression: with shelf_life=1.2, the drain test ``env.now - mfg_date
        # >= shelf_life`` is FP-unstable (e.g. ``9.2 - 8`` rounds to
        # ``1.1999999999999993`` and fails ``>= 1.2``). The daemon's timer was
        # set from ``mfg_date + shelf_life`` and fires exactly at env.now ==
        # next_expiry, so the drain test must use the same additive form;
        # otherwise the daemon falls through with sleep_dt=0 and re-enters at
        # the same simulated time forever. This test would hang prior to the
        # fix; with the fix it completes promptly and drains expired batches.
        inv = _make_inventory(self.env, capacity=1000, initial_level=0,
                              inv_type="perishable", shelf_life=1.2)
        inv.perish_queue.clear()

        # Push one batch every integer tick so head expiries fall on the
        # FP-fragile values 1.2, 2.2, ..., 9.2 etc.
        def steady_puts():
            for t in range(20):
                yield self.env.timeout(1)
                inv.put(10, manufacturing_date=self.env.now)

        self.env.process(steady_puts())
        self.env.run(until=25)
        # Every batch put before t = 25 - 1.2 = 23.8 must have expired and
        # the daemon must have advanced past every one of them — no stalls.
        # Heads with mfg_date <= 23 expire by their respective deadline.
        assert all(d > 25 - 1.2 for d, _ in inv.perish_queue), inv.perish_queue
        assert inv.waste >= 10 * 19  # all 19 of the early batches should be wasted


class TestEndToEndIntegration(unittest.TestCase):
    """§7: end-to-end integration tests for ``create_sc_net`` →
    ``simulate_sc_net`` → aggregated KPIs.

    The examples under ``examples/py/`` were the closest thing to integration
    coverage previously; they don't run under pytest, so a regression in the
    aggregation path (or the canonical ``profit: -4435.0`` invariant) could
    ship green. These tests pin the canonical numbers and verify the
    Network wrapper exposes the same KPIs the dict does.
    """

    def _build_canonical_net(self):
        # Identical to ``examples/py/intro_simple.py`` — keep this in sync
        # with that file so a change to the canonical example is also a
        # signal to update this fixture.
        return scm.create_sc_net(
            nodes=[
                {'ID': 'S1', 'name': 'Supplier1', 'node_type': 'infinite_supplier'},
                {'ID': 'D1', 'name': 'Distributor1', 'node_type': 'distributor',
                 'capacity': 150, 'initial_level': 50, 'inventory_holding_cost': 0.2,
                 'replenishment_policy': scm.SSReplenishment, 'policy_param': {'s': 100, 'S': 150},
                 'product_buy_price': 100, 'product_sell_price': 105},
            ],
            links=[{'ID': 'L1', 'source': 'S1', 'sink': 'D1', 'cost': 5, 'lead_time': lambda: 2}],
            demands=[{'ID': 'd1', 'name': 'Demand1',
                      'order_arrival_model': lambda: 1, 'order_quantity_model': lambda: 10,
                      'demand_node': 'D1'}],
        )

    def test_intro_simple_canonical_profit(self):
        # The canonical -4435.0 profit is the project's smoke-test value;
        # any change here without a matching update to intro_simple.py docs
        # is a real regression.
        sc = self._build_canonical_net()
        scm.simulate_sc_net(sc, sim_time=20, logging=False)
        assert sc["profit"] == -4435.0
        d1_stats = sc["nodes"]["D1"].stats.get_statistics()
        assert d1_stats["inventory_level"] == 100
        assert d1_stats["inventory_carry_cost"] == 410.0
        assert d1_stats["shortage"] == [0, 0]
        assert d1_stats["backorder"] == [0, 0]

    def test_network_wrapper_matches_dict(self):
        # §6.1: ``Network`` should be a transparent wrapper — the dict
        # written by ``simulate_sc_net`` and ``Network.results`` must agree
        # on every result key.
        sc = self._build_canonical_net()
        net = scm.Network(sc)
        net.simulate(sim_time=20, logging=False)
        assert net.has_run is True
        assert net.results["profit"] == sc["profit"]
        assert net.results["shortage"] == sc["shortage"]
        # Lookup helpers route to the same node objects as the dict.
        assert net.node("D1") is sc["nodes"]["D1"]

    def test_log_window_kwarg_runs_to_completion(self):
        # §6.2: dedicated ``log_window=`` kwarg replaces the overloaded
        # ``logging=tuple`` form. The simulation must still drive ``env``
        # all the way to ``sim_time`` regardless of the window choice.
        sc = self._build_canonical_net()
        scm.simulate_sc_net(sc, sim_time=20, log_window=(3, 7))
        assert sc["env"].now >= 20
        assert sc["profit"] == -4435.0

    def test_logging_tuple_back_compat_still_works(self):
        # The deprecation shim must keep accepting ``logging=(start, stop)``
        # so existing user code does not break in the same release as the
        # rename. The shim emits a warning but still runs the simulation.
        sc = self._build_canonical_net()
        scm.simulate_sc_net(sc, sim_time=20, logging=(3, 7))
        assert sc["profit"] == -4435.0


class TestInventoryInvariants(unittest.TestCase):
    """§7: invariant checks for ``Inventory`` that property-based tests
    would have caught the original ``remove_expired`` bug. Hand-rolled here
    rather than introducing ``hypothesis`` as a hard test dep."""

    def setUp(self):
        self.env = simpy.Environment()

    def test_perishable_quantities_match_container_level(self):
        # Sum of perishable batch quantities (excluding the qty=0 sentinels
        # that ``remove_expired`` may leave behind transiently) must equal
        # the SimPy container level after every put/get sequence.
        inv = _make_inventory(self.env, capacity=200, initial_level=0,
                              inv_type="perishable", shelf_life=100)
        inv.perish_queue.clear()
        for d, q in [(1, 10), (3, 30), (2, 20), (5, 15), (4, 25)]:
            inv.put(q, manufacturing_date=d)
        assert sum(q for _, q in inv.perish_queue if q > 0) == inv.level
        # Consume across two batches and re-check.
        get_event, _ = inv.get(35)  # eats (1,10), (2,20), partial of (3,30)
        # SimPy returns immediately when the container has enough to give —
        # ``get_event`` is already triggered, so a process-less check is OK.
        assert sum(q for _, q in inv.perish_queue if q > 0) == inv.level

    def test_on_hand_never_below_container_level_before_dispatch(self):
        # ``on_hand`` (inventory position = shelf + in-transit) must always
        # be >= container.level. The opposite would mean we're shipping
        # against negative in-transit stock.
        env = simpy.Environment()
        sup = scm.Supplier(env=env, ID="S1", name="S", node_type="infinite_supplier")
        inv_node = scm.InventoryNode(
            env=env, ID="D1", name="D", node_type="warehouse",
            capacity=100, initial_level=20, inventory_holding_cost=0.1,
            replenishment_policy=scm.SSReplenishment,
            policy_param={'s': 50, 'S': 80},
            product_sell_price=10, product_buy_price=5,
            logging=False,
        )
        scm.Link(env=env, ID="L1", source=sup, sink=inv_node, lead_time=lambda: 2, cost=1)
        env.run(until=30)
        assert inv_node.inventory.on_hand >= inv_node.inventory.level


class TestEnsureNumericCallable(unittest.TestCase):
    """§6.4: ``ensure_numeric_callable`` must accept scalars, accept zero-arg
    numeric callables, and reject callables that return non-numerics on the
    validation invocation (so passing e.g. a class doesn't crash later)."""

    def test_scalar_is_wrapped(self):
        wrapped = scm.ensure_numeric_callable("x", 7)
        assert callable(wrapped)
        assert wrapped() == 7

    def test_numeric_callable_passes_through(self):
        f = lambda: 3.5
        wrapped = scm.ensure_numeric_callable("x", f)
        assert wrapped is f
        assert wrapped() == 3.5

    def test_class_callable_is_rejected(self):
        # A class is callable (``Foo()`` returns an instance), so the old
        # ``not callable(value)`` guard skipped the wrap and the eventual
        # ``value()`` returned a Foo instance — not a number — that crashed
        # later inside a SimPy generator. Validate-on-call surfaces this
        # immediately at construction.
        class Foo:
            pass
        with pytest.raises(ValueError):
            scm.ensure_numeric_callable("x", Foo)

    def test_string_returning_callable_is_rejected(self):
        with pytest.raises(ValueError):
            scm.ensure_numeric_callable("x", lambda: "two")

    def test_raising_callable_surfaces_typeerror(self):
        def bad():
            raise RuntimeError("nope")
        with pytest.raises(TypeError):
            scm.ensure_numeric_callable("x", bad)


class TestInventoryDestroy(unittest.TestCase):
    """Direct unit tests for ``Inventory.destroy``: the synchronous-drain
    primitive that the Node disruption hook builds on."""

    def setUp(self):
        self.env = _fresh_env()
        self.node = DummyNode(env=self.env)

    def test_destroy_all_drains_container_and_on_hand(self):
        inv = self.node.inventory
        starting = inv.level
        assert starting > 0
        destroyed = inv.destroy()
        assert destroyed == starting
        assert inv.level == 0
        assert inv.on_hand == 0

    def test_destroy_partial_clamps_to_amount(self):
        inv = self.node.inventory
        starting = inv.level
        destroyed = inv.destroy(amount=starting / 2)
        assert destroyed == starting / 2
        assert inv.level == starting - starting / 2

    def test_destroy_clamps_oversize_request(self):
        inv = self.node.inventory
        starting = inv.level
        destroyed = inv.destroy(amount=starting * 100)
        assert destroyed == starting
        assert inv.level == 0

    def test_destroy_zero_or_negative_is_noop(self):
        inv = self.node.inventory
        starting = inv.level
        assert inv.destroy(amount=0) == 0
        assert inv.destroy(amount=-5) == 0
        assert inv.level == starting

    def test_destroy_on_infinite_supplier_is_noop(self):
        env = _fresh_env()
        sup = scm.Supplier(env=env, ID="INF", name="InfSup", node_type="infinite_supplier")
        # infinite_supplier inventory is level=inf; destroy must not blow up
        # and must not touch the level.
        assert sup.inventory.level == float('inf')
        assert sup.inventory.destroy() == 0
        assert sup.inventory.level == float('inf')

    def test_destroy_does_not_signal_inventory_drop(self):
        """Destruction must NOT trigger ``inventory_drop`` — that is the
        replenishment-policy wake signal, and during a disruption window the
        dispatch gate is closed anyway. Triggering it would queue orders to
        fire the moment the node recovers (a wake storm)."""
        # Drain via destroy and check the event has not been succeeded.
        assert not self.node.inventory_drop.triggered
        self.node.inventory.destroy()
        assert not self.node.inventory_drop.triggered

    def test_destroy_perishable_drains_oldest_first(self):
        env = _fresh_env()
        node = DummyNode(env=env)
        # Build a perishable inventory with three known batches and confirm
        # FIFO drain matches the documented head-first order.
        inv = scm.Inventory(env=env, capacity=100, initial_level=0, node=node,
                            replenishment_policy=None, holding_cost=0,
                            shelf_life=10, inv_type="perishable")
        # ``perish_queue`` is a min-heap by mfg_date; pushing in arbitrary
        # order is fine — index 0 is always the oldest.
        inv.put(10, manufacturing_date=1)  # oldest
        inv.put(20, manufacturing_date=5)
        inv.put(30, manufacturing_date=3)
        # Destroy 25 — that's the entire mfg_date=1 batch (10) plus 15 of
        # mfg_date=3 (oldest after the first batch is gone). The mfg_date=5
        # batch is untouched.
        inv.destroy(amount=25)
        remaining = sorted(inv.perish_queue)
        assert remaining == [(3, 15), (5, 20)]

    def test_destroy_perishable_full_wipe(self):
        env = _fresh_env()
        node = DummyNode(env=env)
        inv = scm.Inventory(env=env, capacity=100, initial_level=0, node=node,
                            replenishment_policy=None, holding_cost=0,
                            shelf_life=10, inv_type="perishable")
        inv.put(10, manufacturing_date=1)
        inv.put(20, manufacturing_date=5)
        inv.destroy()  # default = all
        # Heap is empty after a full wipe.
        assert inv.perish_queue == []
        assert inv.level == 0


class TestNodeDisruptionImpactDefaults(unittest.TestCase):
    """Default behavior (no impact specified) must match pre-existing
    semantics so the §validation numbers don't shift."""

    def test_no_impact_leaves_inventory_intact(self):
        env = _fresh_env()
        node = scm.InventoryNode(
            env=env, ID="D1", name="D1", node_type="warehouse",
            capacity=100, initial_level=80, inventory_holding_cost=1.0,
            replenishment_policy=None, policy_param={},
            product_sell_price=10, product_buy_price=5,
            failure_p=0.0, node_disrupt_time=lambda: 5,
            node_recovery_time=lambda: 3,
        )
        # Build a tiny supplier just so the node has somewhere to place orders
        # if a policy ever wanted to (it doesn't here).
        env.run(until=20)
        # No impact set → inventory must remain untouched even though the
        # node went inactive at t=5.
        assert node.inventory.level == 80
        assert node.stats.destroyed_qty == 0
        assert node.stats.destroyed_value == 0


class TestNodeDisruptionImpactDestroyAll(unittest.TestCase):
    """``disruption_impact='destroy_all'`` wipes the node's inventory at the
    active→inactive edge and books the loss into stats."""

    def test_destroy_all_wipes_inventory_at_disruption_edge(self):
        env = _fresh_env()
        node = scm.InventoryNode(
            env=env, ID="D1", name="D1", node_type="warehouse",
            capacity=100, initial_level=80, inventory_holding_cost=0,
            replenishment_policy=None, policy_param={},
            product_sell_price=10, product_buy_price=5,
            node_disrupt_time=lambda: 5, node_recovery_time=lambda: 3,
            disruption_impact="destroy_all",
        )
        env.run(until=4)  # before the disruption — inventory intact
        assert node.inventory.level == 80
        env.run(until=6)  # disruption fired at t=5
        assert node.inventory.level == 0
        assert node.stats.destroyed_qty == 80
        assert node.stats.destroyed_value == 80 * 5  # buy_price = 5

    def test_destroy_all_rolls_into_node_cost(self):
        env = _fresh_env()
        node = scm.InventoryNode(
            env=env, ID="D1", name="D1", node_type="warehouse",
            capacity=100, initial_level=50, inventory_holding_cost=0,
            replenishment_policy=None, policy_param={},
            product_sell_price=10, product_buy_price=4,
            node_disrupt_time=lambda: 2, node_recovery_time=lambda: 100,
            disruption_impact="destroy_all",
        )
        env.run(until=10)
        # destroyed_value (200) is in _cost_components, so it must show up
        # in node_cost after stats are updated. update_stats is called
        # internally by destroy_all_impact, which sums node_cost.
        assert node.stats.destroyed_value == 200
        assert node.stats.node_cost >= 200  # may include carrying cost too

    def test_destroy_all_fires_only_on_active_to_inactive_edge(self):
        """The hook must fire once per disruption, not on every tick during
        the outage. With recovery_time=10 and disrupt_time=5, a 30-tick run
        sees two disruption edges (t=5 and t=20) and stocks 50 each refill —
        but in this test, no replenishment policy means a single edge fires."""
        env = _fresh_env()
        call_count = {"n": 0}

        def custom_impact(node):
            call_count["n"] += 1

        node = scm.InventoryNode(
            env=env, ID="D1", name="D1", node_type="warehouse",
            capacity=100, initial_level=80, inventory_holding_cost=0,
            replenishment_policy=None, policy_param={},
            product_sell_price=10, product_buy_price=5,
            node_disrupt_time=lambda: 5, node_recovery_time=lambda: 4,
            disruption_impact=custom_impact,
        )
        env.run(until=20)
        # Edges: active→inactive at t=5, recover at t=9, inactive again
        # at t=14, recover at t=18, inactive again at t=23 (after run end).
        # So edges in [0, 20]: t=5, t=14 → 2 calls.
        assert call_count["n"] == 2


class TestNodeDisruptionImpactDestroyFraction(unittest.TestCase):
    """``disruption_impact='destroy_fraction'`` wipes a fraction of the
    current level. Fraction may be a scalar or a zero-arg callable that
    samples a fresh value per edge."""

    def test_scalar_fraction(self):
        env = _fresh_env()
        node = scm.InventoryNode(
            env=env, ID="D1", name="D1", node_type="warehouse",
            capacity=100, initial_level=100, inventory_holding_cost=0,
            replenishment_policy=None, policy_param={},
            product_sell_price=10, product_buy_price=5,
            node_disrupt_time=lambda: 5, node_recovery_time=lambda: 100,
            disruption_impact="destroy_fraction",
            disruption_loss_fraction=0.25,
        )
        env.run(until=10)
        assert node.inventory.level == 75
        assert node.stats.destroyed_qty == 25

    def test_callable_fraction_samples_per_edge(self):
        env = _fresh_env()
        # ``ensure_numeric_callable`` invokes the callable once at construction
        # to validate the return type is numeric — that consumes the first
        # value of any stateful generator. So the sequence below has 3 values:
        # [validation, edge_1, edge_2] = [0.5, 0.5, 0.5].
        fractions = iter([0.5, 0.5, 0.5])

        def next_fraction():
            return next(fractions)

        node = scm.InventoryNode(
            env=env, ID="D1", name="D1", node_type="warehouse",
            capacity=200, initial_level=100, inventory_holding_cost=0,
            replenishment_policy=None, policy_param={},
            product_sell_price=10, product_buy_price=5,
            node_disrupt_time=lambda: 5, node_recovery_time=lambda: 4,
            disruption_impact="destroy_fraction",
            disruption_loss_fraction=next_fraction,
        )
        env.run(until=20)
        # Edge 1 (t=5): 100 * 0.5 = 50 destroyed → level = 50
        # Edge 2 (t=14): 50 * 0.5 = 25 destroyed → level = 25
        assert node.inventory.level == 25
        assert node.stats.destroyed_qty == 75

    def test_fraction_out_of_range_raises_on_disruption(self):
        env = _fresh_env()
        node = scm.InventoryNode(
            env=env, ID="D1", name="D1", node_type="warehouse",
            capacity=100, initial_level=80, inventory_holding_cost=0,
            replenishment_policy=None, policy_param={},
            product_sell_price=10, product_buy_price=5,
            node_disrupt_time=lambda: 5, node_recovery_time=lambda: 100,
            disruption_impact="destroy_fraction",
            disruption_loss_fraction=1.5,  # invalid — caught at first edge
        )
        with pytest.raises(ValueError):
            env.run(until=10)


class TestNodeDisruptionImpactCustomCallable(unittest.TestCase):
    """User-supplied callables are the escape hatch for arbitrary effects:
    contamination, capacity damage, partial spoilage with non-uniform
    distributions, etc."""

    def test_custom_callable_runs_with_node_arg(self):
        env = _fresh_env()
        captured = {"node": None}

        def impact(node):
            captured["node"] = node
            # User decides what to do — here, nuke half via the public destroy API.
            node.inventory.destroy(amount=node.inventory.level * 0.5,
                                   reason="contamination")

        node = scm.InventoryNode(
            env=env, ID="D1", name="D1", node_type="warehouse",
            capacity=100, initial_level=60, inventory_holding_cost=0,
            replenishment_policy=None, policy_param={},
            product_sell_price=10, product_buy_price=5,
            node_disrupt_time=lambda: 5, node_recovery_time=lambda: 100,
            disruption_impact=impact,
        )
        env.run(until=10)
        assert captured["node"] is node
        assert node.inventory.level == 30


class TestNodeDisruptionImpactValidation(unittest.TestCase):
    def test_unknown_string_preset_raises(self):
        env = _fresh_env()
        with pytest.raises(ValueError):
            scm.InventoryNode(
                env=env, ID="D1", name="D1", node_type="warehouse",
                capacity=100, initial_level=10, inventory_holding_cost=0,
                replenishment_policy=None, policy_param={},
                product_sell_price=10, product_buy_price=5,
                disruption_impact="explode_everything",
            )

    def test_non_callable_non_string_raises(self):
        env = _fresh_env()
        with pytest.raises(ValueError):
            scm.InventoryNode(
                env=env, ID="D1", name="D1", node_type="warehouse",
                capacity=100, initial_level=10, inventory_holding_cost=0,
                replenishment_policy=None, policy_param={},
                product_sell_price=10, product_buy_price=5,
                disruption_impact=42,  # not str, not callable, not None
            )

    def test_none_and_lowercase_none_string_are_equivalent(self):
        env1 = _fresh_env()
        env2 = _fresh_env()
        n1 = scm.InventoryNode(
            env=env1, ID="A", name="A", node_type="warehouse",
            capacity=10, initial_level=5, inventory_holding_cost=0,
            replenishment_policy=None, policy_param={},
            product_sell_price=10, product_buy_price=5,
            disruption_impact=None,
        )
        n2 = scm.InventoryNode(
            env=env2, ID="A", name="A", node_type="warehouse",
            capacity=10, initial_level=5, inventory_holding_cost=0,
            replenishment_policy=None, policy_param={},
            product_sell_price=10, product_buy_price=5,
            disruption_impact="None",
        )
        assert n1._disruption_impact_fn is None
        assert n2._disruption_impact_fn is None


class TestManufacturerDisruptionImpactDestroyAll(unittest.TestCase):
    """For a Manufacturer, ``destroy_all`` must wipe both the finished-goods
    inventory and the per-raw-material counts — the spirit of "everything
    physical at this site is gone" applies to both stockpiles. The
    Manufacturer's own behavior loop continually consumes/refills raw
    materials, so this test invokes the impact handler directly on a
    constructed manufacturer to isolate the destroy-all mechanism from
    the production schedule."""

    def test_destroy_all_wipes_finished_and_raw_inventories(self):
        from SupplyNetPy.Components.core import _destroy_all_impact

        env = _fresh_env()
        rm = scm.RawMaterial(ID="RM1", name="RM1", extraction_quantity=10,
                             extraction_time=2, mining_cost=1, cost=2)
        sup = scm.Supplier(env=env, ID="S1", name="S1", node_type="supplier",
                           capacity=100, initial_level=100,
                           inventory_holding_cost=0, raw_material=rm)
        prod = scm.Product(ID="P1", name="P1", manufacturing_cost=1,
                           manufacturing_time=1, sell_price=20,
                           raw_materials=[(rm, 1)], batch_size=5)
        mfr = scm.Manufacturer(
            env=env, ID="M1", name="M1",
            capacity=100, initial_level=10, inventory_holding_cost=0,
            product_sell_price=20, replenishment_policy=None, policy_param={},
            product=prod, supplier_selection_policy=scm.SelectFirst,
        )
        scm.Link(env=env, ID="L1", source=sup, sink=mfr, lead_time=lambda: 1, cost=0)
        # Force a known raw_inventory_counts state. Bypassing env.run avoids
        # the behavior loop consuming or refilling these counts before the
        # destroy call can observe them.
        mfr.raw_inventory_counts[rm.ID] = 50

        _destroy_all_impact(mfr)

        assert mfr.inventory.level == 0
        # Key may persist with value 0 — that's expected; the dict isn't
        # rebuilt, only its values are zeroed.
        assert mfr.raw_inventory_counts.get(rm.ID, 0) == 0
        # destroyed_qty covers both finished (10) and raw (50) units.
        assert mfr.stats.destroyed_qty == 60
        # destroyed_value: finished priced at product.buy_price (which the
        # Manufacturer init set to manufacturing_cost + raw_material cost
        # = 1 + 2 = 3); raw priced at rm.cost = 2.
        # 10*3 + 50*2 = 130
        assert mfr.stats.destroyed_value == 130