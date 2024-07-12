import sys
sys.path.insert(1, 'src/SupplyNetPy/Model')
import Inventories as inv
import Core as sccore
import simpy
import pytest

## -- Tests for 'Inventories' module starts here -- ##
def test_capacity_negative():
    env = simpy.Environment()
    with pytest.raises(ValueError):
        inv1 = inv.Inventory(env,capacity=-100, holding_cost=10, reorder_level=0)

def test_capacity_zero():
    env = simpy.Environment()
    with pytest.raises(ValueError):
        inv1 = inv.Inventory(env,capacity=0, holding_cost=10, reorder_level=0)

def test_capacity_positive():
    env = simpy.Environment()
    inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=0)
    assert isinstance(inv1,object)

def test_hold_cost_negative():
    env = simpy.Environment()
    with pytest.raises(ValueError):
        inv1 = inv.Inventory(env,capacity=100, holding_cost=-10, reorder_level=0)

def test_hold_cost_zero():
    env = simpy.Environment()
    with pytest.raises(ValueError):
        inv1 = inv.Inventory(env,capacity=100, holding_cost=0, reorder_level=0)

def test_hold_cost_positive():
    env = simpy.Environment()
    inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=0)
    assert isinstance(inv1,object)
    

def test_reorder_lvl_negative():
    env = simpy.Environment()
    with pytest.raises(ValueError):
        inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=-10)

def test_reorder_lvl_lt_capacity():
    env = simpy.Environment()
    inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=99)
    assert isinstance(inv1,object)

def test_reorder_lvl_gt_capacity():
    env = simpy.Environment()
    with pytest.raises(ValueError):
        inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=200)

def test_replenishment_policy_sS():
    env = simpy.Environment()
    inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, replenishment_policy="sS")
    assert isinstance(inv1,object)

def test_replenishment_policy_Periodic():
    env = simpy.Environment()
    inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, replenishment_policy="Periodic")
    assert isinstance(inv1,object)

def test_replenishment_policy_JIT():
    env = simpy.Environment()
    inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, replenishment_policy="JustInTime")
    assert isinstance(inv1,object)

def test_replenishment_policy_other():
    env = simpy.Environment()
    with pytest.raises(ValueError):
        inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, replenishment_policy="other")

def test_reorder_period_negative():
    env = simpy.Environment()
    with pytest.raises(ValueError):
        inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, reorder_period=-3)

def test_reorder_period_zero():
    env = simpy.Environment()
    with pytest.raises(ValueError):
        inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, reorder_period=0)
    
def test_reorder_period_positive():
    env = simpy.Environment()
    inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, reorder_period=3)
    assert isinstance(inv1,object)

def test_inventory_type_single():
    env = simpy.Environment()
    inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, inventory_type="Single")
    assert isinstance(inv1,object)

def test_inventory_type_perishable():
    env = simpy.Environment()
    inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, inventory_type="Perishable")
    assert isinstance(inv1,object)

def test_inventory_type_mixed():
    env = simpy.Environment()
    item1 = inv.Product(sku=123, name="Tea", description="Tea", cost=10, profit=1, product_type="perishable", shelf_life=180)
    item2 = inv.Product(sku=233, name="Sugar", description="Sugar", cost=10, profit=1, product_type="perishable", shelf_life=180)
    inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, inventory_type="Mixed", products=[item1,item2])
    assert isinstance(inv1,object)

def test_inventory_type_other():
    env = simpy.Environment()
    with pytest.raises(ValueError):
        inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, inventory_type="other")

def test_produts_none_with_mixed():
    env = simpy.Environment()
    with pytest.raises(ValueError):
        inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, inventory_type="Mixed")

def test_produts_with_mixed_one():
    env = simpy.Environment()
    item1 = inv.Product(sku=123, name="Tea", description="Tea", cost=10, profit=1, product_type="perishable", shelf_life=180)
    with pytest.raises(ValueError):
        inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, inventory_type="Mixed", products=[item1])

def test_produts_with_mixed_gt_one():
    env = simpy.Environment()
    item1 = inv.Product(sku=123, name="Tea", description="Tea", cost=10, profit=1, product_type="perishable", shelf_life=180)
    item2 = inv.Product(sku=233, name="Sugar", description="Sugar", cost=10, profit=1, product_type="perishable", shelf_life=180)
    inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, inventory_type="Mixed", products=[item1,item2])
    assert isinstance(inv1,object)

def test_produts_none_without_mixed():
    env = simpy.Environment()
    item1 = inv.Product(sku=123, name="Tea", description="Tea", cost=10, profit=1, product_type="perishable", shelf_life=180)
    inv1 = inv.Inventory(env,capacity=100, holding_cost=10, reorder_level=20, inventory_type="Single",products=[item1])
    assert isinstance(inv1,object)
## -- Tests for 'Inventories' module ends here -- ##

## -- Tests for 'Core' module starts here -- ##
## -- Tests for Links starts -- ##
class TestLink:
    env = simpy.Environment()
    product1 = inv.Product(sku="12325", name="Bottle", description="Plastic Bottle", cost=10, profit=2, product_type="non-perishable", shelf_life=None)
    sup1 = sccore.Supplier(env=env, name="supplier1", node_id="411", location="Goa", inv_capacity=800, inv_holding_cost=1)
    man1 = sccore.Manufacturer(env=env,name="Manufacturer1", node_id="311",location="Vasco", products=[product1], production_cost=100, production_level=200, inv_capacity=400, inv_holding_cost=3, reorder_level=150)
    dis1 = sccore.Distributor(env=env,name="distributor1",node_id="321",location="Panaji",products=[product1],inv_capacity=200,inv_holding_cost=3,reorder_level=100)
    ret1 = sccore.Retailer(env=env, name="Retailer1", node_id="211", location="Ponda",products=[product1],inv_capacity=200, inv_holding_cost=4, reorder_level= 50)

    def test_lead_time_negative(self):        
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=-6, transportation_cost=100, link_distance=500)

    def test_lead_time_positive(self):
        edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=500)
        assert isinstance(edge_sup1_man,object)

    def test_transportation_cost_negative(self):        
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=-100, link_distance=500)

    def test_transportation_cost_positive(self):
        edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=500)
        assert isinstance(edge_sup1_man,object)

    def test_link_distance_negative(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=-500)

    def test_link_distance_zero(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=0)

    def test_link_distance_positive(self):
        edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=500)
        assert isinstance(edge_sup1_man,object)

    def test_transportation_type_other(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=0,
                                        transportation_type = "any")
    
    def test_transportation_type_road(self):
        edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=500,transportation_type = "road")
        assert isinstance(edge_sup1_man,object)

    def test_transportation_type_air(self):
        edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=500,transportation_type = "air")
        assert isinstance(edge_sup1_man,object)

    def test_transportation_type_water(self):
        edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=500,transportation_type = "water")
        assert isinstance(edge_sup1_man,object)

    def test_max_load_capacity_negative(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=500, max_load_capacity=-100)

    def test_max_load_capacity_positive(self):
        edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=500, max_load_capacity=100)
        assert isinstance(edge_sup1_man,object)

    def test_min_shipment_quantity_negative(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=500, min_shipment_quantity=-100)
    
    def test_min_shipment_quantity_positive(self):
        edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=500, min_shipment_quantity=100)
        assert isinstance(edge_sup1_man,object)

    def test_link_supplier_to_retailer(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.ret1, lead_time=6, transportation_cost=100, link_distance=500)

    def test_link_supplier_to_distributor(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.dis1, lead_time=6, transportation_cost=100, link_distance=500)

    def test_link_supplier_to_manufacturer(self):
        edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=500)
        assert isinstance(edge_sup1_man,object)

    def test_link_supplier_to_supplier(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.sup1, to_node=self.sup1, lead_time=6, transportation_cost=100, link_distance=500)
    
    def test_link_manufacturer_to_supplier(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.man1, to_node=self.sup1, lead_time=6, transportation_cost=100, link_distance=500)

    def test_link_manufacturer_to_manufacturer(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.man1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=500)

    def test_link_manufacturer_to_distributor(self):
        edge_sup1_man = sccore.Link(from_node=self.man1, to_node=self.dis1, lead_time=6, transportation_cost=100, link_distance=500)
        assert isinstance(edge_sup1_man,object)

    def test_link_manufacturer_to_retailer(self):
        edge_sup1_man = sccore.Link(from_node=self.man1, to_node=self.ret1, lead_time=6, transportation_cost=100, link_distance=500)
        assert isinstance(edge_sup1_man,object)
    
    def test_link_distributor_to_supplier(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.dis1, to_node=self.sup1, lead_time=6, transportation_cost=100, link_distance=500)
    
    def test_link_distributor_to_manufacturer(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.dis1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=500)

    def test_link_distributor_to_distributor(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.dis1, to_node=self.dis1, lead_time=6, transportation_cost=100, link_distance=500)

    def test_link_distributor_to_retailer(self):
        edge_sup1_man = sccore.Link(from_node=self.dis1, to_node=self.ret1, lead_time=6, transportation_cost=100, link_distance=500)
        assert isinstance(edge_sup1_man,object)
    
    def test_link_retailer_to_supplier(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.ret1, to_node=self.sup1, lead_time=6, transportation_cost=100, link_distance=500)
    
    def test_link_retailer_to_manufacturer(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.ret1, to_node=self.man1, lead_time=6, transportation_cost=100, link_distance=500)

    def test_link_retailer_to_distributor(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.ret1, to_node=self.dis1, lead_time=6, transportation_cost=100, link_distance=500)

    def test_link_retailer_to_retailer(self):
        with pytest.raises(ValueError):
            edge_sup1_man = sccore.Link(from_node=self.ret1, to_node=self.ret1, lead_time=6, transportation_cost=100, link_distance=500)
## -- Tests for Links ends -- ##
## -- Tests for Node starts -- ##
def test_node_type_other():
    env = simpy.Environment()
    with pytest.raises(ValueError):
        node1 = sccore.Node(env=env,name="other!",node_id="666",node_type="other",location="Goa")

def test_node_type_supplier():
    env = simpy.Environment()
    node1 = sccore.Node(env=env,name="supplier1",node_id="511",node_type="SUPPLIER",location="Goa")
    node2 = sccore.Node(env=env,name="supplier1",node_id="512",node_type="Supplier",location="Goa")
    assert isinstance(node1,object)
    assert isinstance(node2,object)

def test_node_type_manufacturer():
    env = simpy.Environment()
    node1 = sccore.Node(env=env,name="manufacturer",node_id="411",node_type="MANUFACTURER",location="Goa")
    node2 = sccore.Node(env=env,name="manufacturer",node_id="412",node_type="Manufacturer",location="Goa")
    assert isinstance(node1,object)
    assert isinstance(node2,object)

def test_node_type_distributor():
    env = simpy.Environment()
    node1 = sccore.Node(env=env,name="distributor",node_id="311",node_type="DISTRIBUTOR",location="Goa")
    node2 = sccore.Node(env=env,name="distributor",node_id="312",node_type="Distributor",location="Goa")
    node3 = sccore.Node(env=env,name="distributor",node_id="313",node_type="WAREHOUSE",location="Goa")
    node4 = sccore.Node(env=env,name="distributor",node_id="314",node_type="warehouse",location="Goa")
    assert isinstance(node1,object)
    assert isinstance(node2,object)
    assert isinstance(node3,object)
    assert isinstance(node4,object)

def test_node_type_retailer():
    env = simpy.Environment()
    node1 = sccore.Node(env=env,name="retailer",node_id="11",node_type="RETAILER",location="Goa")
    node2 = sccore.Node(env=env,name="retailer",node_id="12",node_type="Retailer",location="Goa")
    assert isinstance(node1,object)
    assert isinstance(node2,object)

def test_node_disconnected_ret():
    env = simpy.Environment()
    product1 = inv.Product(sku="12325", name="Bottle", description="Plastic Bottle",cost=10,profit=2, product_type="non-perishable", shelf_life=None)
    ret1 = sccore.Retailer(env=env, name="Retailer1", node_id="211", location="Ponda",products=[product1],inv_capacity=200, inv_holding_cost=4, reorder_level= 50)
    with pytest.raises(ValueError):
        env.run(1)

def test_node_disconnected_dis():
    env = simpy.Environment()
    product1 = inv.Product(sku="12325", name="Bottle", description="Plastic Bottle",cost=10,profit=2, product_type="non-perishable", shelf_life=None)
    dis1 = sccore.Distributor(env=env,name="distributor1",node_id="321",location="Panaji",products=[product1],inv_capacity=200,inv_holding_cost=3,reorder_level=100)
    with pytest.raises(ValueError):
        env.run(1)

def test_node_disconnected_man():
    env = simpy.Environment()
    product1 = inv.Product(sku="12325", name="Bottle", description="Plastic Bottle",cost=10,profit=2, product_type="non-perishable", shelf_life=None)
    man1 = sccore.Manufacturer(env=env,name="Manufacturer1", node_id="311",location="Vasco",products=[product1],production_cost=100, production_level=200, inv_capacity=400, inv_holding_cost=3, reorder_level=150)
    with pytest.raises(ValueError):
        env.run(1)

def test_node_disconnected_sup():
    env = simpy.Environment()
    sup1 = sccore.Supplier(env=env, name="supplier1", node_id="411", location="Goa", inv_capacity=800, inv_holding_cost=1)
    env.run(1)
    assert isinstance(sup1,object)

## -- Tests for Node ends -- ##
## -- Tests for 'Core' module ends here -- ##