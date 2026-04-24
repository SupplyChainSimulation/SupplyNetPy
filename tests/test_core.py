import random
import unittest
import pytest
import simpy
import SupplyNetPy.Components as scm

# Shared module-level environment used by DummyNode (below). Tests that need
# isolation create their own env in setUp; DummyNode's suppliers/links still
# reference this one — acceptable for the existing tests, which only exercise
# DummyNode for static inspection (supplier selection, init checks).
env = simpy.Environment()

class TestRawMaterial(unittest.TestCase):
    """
    Testing RawMaterial
    """
    raw_material = scm.RawMaterial(ID="RM1",
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
    Testing Product class
    """
    raw_material1 = scm.RawMaterial(ID="RM1", name="Raw Material 1", extraction_quantity=10, extraction_time=2, mining_cost=1, cost=2)
    raw_material2 = scm.RawMaterial(ID="RM2", name="Raw Material 2", extraction_quantity=5, extraction_time=1, mining_cost=0.5, cost=1)

    product = scm.Product(
        ID="P1",
        name="Product 1",
        manufacturing_cost=10,
        manufacturing_time=5,
        sell_price=20,
        raw_materials=[(raw_material1, 2), (raw_material2, 3)],
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
    def __init__(self):
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
        self.env = simpy.Environment()
        self.node = DummyNode()
        self.node.env = self.env

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
        self.env = simpy.Environment()
        self.node = DummyNode()
        self.node.env = self.env

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
        self.env = simpy.Environment()
        self.node = DummyNode()
        self.node.env = self.env

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
        self.env = simpy.Environment()
        self.node = DummyNode()
        self.node.env = self.env

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
        self.env = simpy.Environment()
        self.node = DummyNode()
        self.node.env = self.env

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
        self.env = simpy.Environment()
        self.node = DummyNode()
        self.node.env = self.env

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
        self.env = simpy.Environment()
        self.node = DummyNode()
        self.node.env = self.env

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
        self.env = simpy.Environment()
        self.node = DummyNode()
        self.node.env = self.env

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
        expected = {"inventory_carry_cost", "inventory_spend_cost", "transportation_cost"}
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
        assert stats["orders_shortage"] == [0, 0]
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