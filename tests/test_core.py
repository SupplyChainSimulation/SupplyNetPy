import unittest
import pytest
import simpy 
import SupplyNetPy.Components as scm
from SupplyNetPy.Components.logger import GlobalLogger

env = simpy.Environment()
global_logger = GlobalLogger() # create a global logger
inventory = simpy.Container(env, init=100, capacity=1000) # create a global inventory for testing

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