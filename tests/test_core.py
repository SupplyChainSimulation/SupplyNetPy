import unittest
import pytest
from simpy import Environment
from SupplyNetPy.Components.core import *

def test_raw_material_init():
    raw_material = RawMaterial(ID="RM1", name="Raw Material 1", extraction_quantity=30, extraction_time=3, cost=1)
    assert raw_material.ID == "RM1"
    assert raw_material.name == "Raw Material 1"
    assert raw_material.extraction_quantity == 30
    assert raw_material.extraction_time == 3
    assert raw_material.cost == 1

def test_raw_material_str():
    raw_material = RawMaterial(ID="RM1", name="Raw Material 1", extraction_quantity=30, extraction_time=3, cost=1)
    assert str(raw_material) == "Raw Material 1"

def test_raw_material_repr():
    raw_material = RawMaterial(ID="RM1", name="Raw Material 1", extraction_quantity=30, extraction_time=3, cost=1)
    assert repr(raw_material) == "Raw Material 1"

def test_raw_material_get_info():
    raw_material = RawMaterial(ID="RM1", name="Raw Material 1", extraction_quantity=30, extraction_time=3, cost=1)
    info = raw_material.get_info()
    assert info["ID"] == "RM1"
    assert info["name"] == "Raw Material 1"
    assert info["extraction_quantity"] == 30
    assert info["extraction_time"] == 3
    assert info["cost"] == 1

class TestProduct(unittest.TestCase):
    def setUp(self):
        self.product = Product(ID="P1", name="Product 1", manufacturing_cost=100, manufacturing_time=10, sell_price=220, raw_materials=[{"raw_material": default_raw_material, "quantity": 9}], units_per_cycle=30)

    def test_get_info(self):
        expected_info = {
            "ID": "P1",
            "name": "Product 1",
            "manufacturing_cost": 100,
            "manufacturing_time": 10,
            "sell_price": 220,
            "buy_price": 0,
            "raw_materials": [{"raw_material": default_raw_material, "quantity": 9}],
            "units_per_cycle": 30
        }
        self.assertEqual(self.product.get_info(), expected_info)

    def test_str(self):
        self.assertEqual(str(self.product), "Product 1")

    def test_repr(self):
        self.assertEqual(repr(self.product), "Product 1")

class TestNode(unittest.TestCase):
    def setUp(self):
        self.node = Node(ID="N1", name="Node 1", node_type="supplier")

    def test_get_info(self):
        expected_info = {
            "ID": "N1",
            "name": "Node 1",
            "node_type": "supplier"
        }
        self.assertEqual(self.node.get_info(), expected_info)

    def test_str(self):
        self.assertEqual(str(self.node), "Node 1")

    def test_repr(self):
        self.assertEqual(repr(self.node), "Node 1")

class TestLink(unittest.TestCase):
    def setUp(self):
        self.node1 = Node(ID="N1", name="Node 1", node_type="supplier")
        self.node2 = Node(ID="N2", name="Node 2", node_type="supplier")
        self.link = Link(ID="L1", name="Link 1", source=self.node1, target=self.node2, cost=10, time=5)

    def test_get_info(self):
        expected_info = {
            "ID": "L1",
            "name": "Link 1",
            "source": self.node1,
            "target": self.node2,
            "cost": 10,
            "time": 5
        }
        self.assertEqual(self.link.get_info(), expected_info)

    def test_str(self):
        self.assertEqual(str(self.link), "Link 1")

    def test_repr(self):
        self.assertEqual(repr(self.link), "Link 1")

class TestSupplier(unittest.TestCase):
    def setUp(self):
        self.supplier = Supplier(ID="S1", name="Supplier 1", raw_materials=[{"raw_material": default_raw_material, "quantity": 10}], extraction_time=5, extraction_quantity=30)

    def test_get_info(self):
        expected_info = {
            "ID": "S1",
            "name": "Supplier 1",
            "raw_materials": [{"raw_material": default_raw_material, "quantity": 10}],
            "extraction_time": 5,
            "extraction_quantity": 30
        }
        self.assertEqual(self.supplier.get_info(), expected_info)

    def test_str(self):
        self.assertEqual(str(self.supplier), "Supplier 1")

    def test_repr(self):
        self.assertEqual(repr(self.supplier), "Supplier 1")

class TestManufacturer(unittest.TestCase):
    def setUp(self):
        self.manufacturer = Manufacturer(ID="M1", name="Manufacturer 1", products=[{"product": default_product, "quantity": 10}], manufacturing_time=5, manufacturing_quantity=30)
    
    def test_get_info(self):
        expected_info = {
            "ID": "M1",
            "name": "Manufacturer 1",
            "products": [{"product": default_product, "quantity": 10}],
            "manufacturing_time": 5,
            "manufacturing_quantity": 30
        }
        self.assertEqual(self.manufacturer.get_info(), expected_info)

    def test_str(self):
        self.assertEqual(str(self.manufacturer), "Manufacturer 1")

    def test_repr(self):
        self.assertEqual(repr(self.manufacturer), "Manufacturer 1")

        

