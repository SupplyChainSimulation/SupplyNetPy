import random
import re
import unittest
import warnings
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

class _ScriptedRandom(random.Random):
    """A random number generator that returns the given values from random(), and counts the calls."""

    def __init__(self, values):
        super().__init__(0)
        self.values = list(values)
        self.calls = 0

    def random(self):
        self.calls += 1
        return self.values.pop(0)


_PROBS = {"S1": 0.5, "S2": 0.3, "S3": 0.2}


def _probabilistic_net(env, probabilities=_PROBS, link_ids=("S1", "S2", "S3"), site_kw=None, sup_kw=None, **param):
    """Three infinite suppliers S1, S2, S3 linked in that order to distributor D1, which uses SelectProbabilistic."""
    sup_kw = sup_kw or {}
    sups = {i: scm.Supplier(env=env, ID=i, name=i, node_type="infinite_supplier", **sup_kw.get(i, {}))
            for i in ("S1", "S2", "S3")}
    if probabilities is not None:
        param["probabilities"] = probabilities
    site_kw = dict(capacity=10**7, initial_level=0, replenishment_policy=None, policy_param=None) | (site_kw or {})
    d1 = scm.InventoryNode(env=env, ID="D1", name="D1", node_type="distributor", inventory_holding_cost=0,
                           product_buy_price=1, product_sell_price=2,
                           supplier_selection_policy=scm.SelectProbabilistic, supplier_selection_param=param,
                           **site_kw)
    links = [scm.Link(env=env, ID=f"L{n}", source=sups[i], sink=d1, cost=1, lead_time=lambda: 1)
             for n, i in enumerate(link_ids, start=1)]
    return sups, d1, links


def _sequence(seed=None, n=50, **param):
    """The suppliers chosen for n orders in a fresh network."""
    if seed is not None:
        param["seed"] = seed
    _, d1, _ = _probabilistic_net(_fresh_env(), **param)
    return [d1.selection_policy.select(1).source.ID for _ in range(n)]


class TestSelectProbabilistic(unittest.TestCase):
    """SelectProbabilistic chooses each replenishment order's supplier at random, with a probability per supplier."""

    def test_stacking(self):
        rng = _ScriptedRandom([0.49, 0.5, 0.79, 0.8, 0.999])
        _, d1, (l1, l2, l3) = _probabilistic_net(_fresh_env(), rng=rng)
        assert [d1.selection_policy.select(10) for _ in range(5)] == [l1, l2, l2, l3, l3]

    def test_one_draw_per_select(self):
        rng = _ScriptedRandom([0.1] * 10)
        sups, d1, _ = _probabilistic_net(_fresh_env(), rng=rng)
        for _ in range(3):
            d1.selection_policy.select(10)
        sups["S1"].node_status = "inactive"
        sups["S2"].node_status = "inactive"  # only S3 can take an order
        for _ in range(2):
            d1.selection_policy.select(10)
        assert rng.calls == 5

    def test_zero_probability_never_chosen(self):
        _, d1, (l1, l2, l3) = _probabilistic_net(_fresh_env(), probabilities={"S1": 0.0, "S2": 1.0, "S3": 0.0},
                                                 seed=3)
        assert all(d1.selection_policy.select(1) is l2 for _ in range(200))

    def test_only_zero_probability_supplier_working_blocks(self):
        env = _fresh_env()
        sups, d1, (l1, l2, l3) = _probabilistic_net(env, probabilities={"S1": 1.0, "S2": 0.0, "S3": 0.0}, seed=3)
        sups["S1"].node_status = "inactive"
        d1.place_order(10)
        env.run(until=2)
        assert d1.stats.blocked == [1, 10]
        assert l1.stats.blocked == [1, 10]
        assert sups["S2"].stats.demand_received == [0, 0]
        assert d1.stats.fulfillment_received == [0, 0]

    def test_rescale_keeps_ratios(self):
        rng = _ScriptedRandom([0.55, 0.65])
        sups, d1, (l1, l2, l3) = _probabilistic_net(_fresh_env(), rng=rng)
        sups["S1"].node_status = "inactive"
        # S2 and S3 share the orders 0.6 to 0.4: 0.55 x 0.5 = 0.275 < 0.3, 0.65 x 0.5 = 0.325 >= 0.3
        assert d1.selection_policy.select(10) is l2
        assert d1.selection_policy.select(10) is l3

    def test_block_lands_on_disrupted_supplier(self):
        env = _fresh_env()
        sups, d1, (l1, l2, l3) = _probabilistic_net(env, rng=_ScriptedRandom([0.1]), on_disruption="block")
        sups["S1"].node_status = "inactive"
        d1.place_order(10)
        env.run(until=2)
        assert d1.stats.blocked == [1, 10]
        assert l1.stats.blocked == [1, 10]
        assert d1.stats.fulfillment_received == [0, 0]

    def test_shares_close_to_probabilities(self):
        _, d1, links = _probabilistic_net(_fresh_env(), seed=1)
        chosen = [d1.selection_policy.select(1) for _ in range(4000)]
        for link, p in zip(links, (0.5, 0.3, 0.2)):
            assert abs(chosen.count(link) / 4000 - p) < 0.03, link.ID

    def test_same_seed_same_sequence(self):
        assert _sequence(seed=7) == _sequence(seed=7)

    def test_different_seed_differs(self):
        assert _sequence(seed=7) != _sequence(seed=8)

    def test_set_seed_repeats_run(self):
        scm.set_seed(3)
        first = _sequence()
        scm.set_seed(3)
        assert _sequence() == first

    def test_site_rng_repeats_run(self):
        def run():
            _, d1, _ = _probabilistic_net(_fresh_env(), site_kw={"rng": random.Random(9)})
            return [d1.selection_policy.select(1).source.ID for _ in range(50)]
        assert run() == run()

    def test_draws_do_not_disturb_other_random_numbers(self):
        # D1 is disrupted at random with its own generator. With a seed, the
        # policy's draws come from its own generator, so D1's disruptions are
        # the same as with SelectFirst, which draws nothing. (All suppliers are
        # alike, so the choice of supplier does not change D1's run.)
        def run(policy, param):
            env = _fresh_env()
            sups = {i: scm.Supplier(env=env, ID=i, name=i, node_type="infinite_supplier") for i in ("S1", "S2", "S3")}
            d1 = scm.InventoryNode(env=env, ID="D1", name="D1", node_type="distributor", capacity=100,
                                   initial_level=0, inventory_holding_cost=0,
                                   replenishment_policy=scm.SSReplenishment, policy_param={"s": 20, "S": 50},
                                   product_buy_price=1, product_sell_price=2, failure_p=0.1,
                                   node_recovery_time=lambda: 2, rng=random.Random(6),
                                   supplier_selection_policy=policy, supplier_selection_param=param)
            for n, i in enumerate(("S1", "S2", "S3"), start=1):
                scm.Link(env=env, ID=f"L{n}", source=sups[i], sink=d1, cost=1, lead_time=lambda: 1)
            scm.Demand(env=env, ID="C1", name="C1", order_arrival_model=lambda: 1,
                       order_quantity_model=lambda: 5, demand_node=d1)
            env.run(until=100)
            assert d1.stats.demand_placed[0] > 5
            # The generator's state shows how many numbers were drawn from it.
            return d1.rng.getstate(), d1.stats.disruptions, d1.stats.demand_placed
        assert run(scm.SelectProbabilistic, {"probabilities": _PROBS, "seed": 5}) == run(scm.SelectFirst, None)

    def test_mode_default_is_dynamic(self):
        _, d1, _ = _probabilistic_net(_fresh_env(), seed=1)
        assert d1.selection_policy.mode == "dynamic"

    def test_fixed_mode_rejected(self):
        with pytest.raises(ValueError, match="fixed"):
            scm.InventoryNode(env=_fresh_env(), ID="D1", name="D1", node_type="distributor", capacity=10,
                              initial_level=0, inventory_holding_cost=0, replenishment_policy=None,
                              policy_param=None, product_buy_price=1, product_sell_price=2,
                              supplier_selection_policy=scm.SelectProbabilistic, supplier_selection_mode="fixed",
                              supplier_selection_param={"probabilities": _PROBS})

    def test_invalid_probabilities(self):
        for bad in ({"S1": 0.5, "S2": 0.3, "S3": 0.3}, {"S1": -0.1, "S2": 1.1, "S3": 0.0},
                    {"S1": 0.0, "S2": 0.0, "S3": 0.0}, [0.5, 0.5], {"S1": True, "S2": 0.0, "S3": 0.0},
                    {"S1": "0.5", "S2": 0.5, "S3": 0.0}):
            with pytest.raises(ValueError):
                _probabilistic_net(_fresh_env(), probabilities=bad)

    def test_normalized_random_weights_accepted(self):
        r = random.Random(2)
        w = [r.random() for _ in range(3)]
        probabilities = dict(zip(("S1", "S2", "S3"), (x / sum(w) for x in w)))
        _, d1, (l1, l2, l3) = _probabilistic_net(_fresh_env(), probabilities=probabilities,
                                                 rng=_ScriptedRandom([0.9999999999999999]))
        assert d1.selection_policy.select(1) is l3

    def test_seed_and_rng_together(self):
        with pytest.raises(ValueError):
            _probabilistic_net(_fresh_env(), seed=1, rng=random.Random(1))

    def test_rng_must_be_a_random_generator(self):
        with pytest.raises(ValueError):
            _probabilistic_net(_fresh_env(), rng=5)

    def test_unknown_on_disruption(self):
        with pytest.raises(ValueError):
            _probabilistic_net(_fresh_env(), on_disruption="wait")

    def test_unknown_setting_warns(self):
        with pytest.warns(UserWarning, match="quota"):
            _probabilistic_net(_fresh_env(), seed=1, quota=True)

    def test_link_without_probability(self):
        _, d1, _ = _probabilistic_net(_fresh_env(), probabilities={"S1": 0.5, "S2": 0.5}, seed=1)
        with pytest.raises(ValueError, match="S3"):
            d1.selection_policy.select(1)

    def test_probability_without_link(self):
        _, d1, _ = _probabilistic_net(_fresh_env(), link_ids=("S1", "S2"), seed=1)
        with pytest.raises(ValueError, match="S3"):
            d1.selection_policy.select(1)

    def test_two_links_from_one_supplier(self):
        _, d1, _ = _probabilistic_net(_fresh_env(), link_ids=("S1", "S2", "S3", "S1"), seed=1)
        with pytest.raises(ValueError, match="S1"):
            d1.selection_policy.select(1)

    def test_link_without_probability_found_in_a_run_with_env_run(self):
        env = _fresh_env()
        _probabilistic_net(env, probabilities={"S1": 0.5, "S2": 0.5}, seed=1,
                           site_kw={"replenishment_policy": scm.SSReplenishment, "policy_param": {"s": 20, "S": 50}})
        with pytest.raises(ValueError, match="S3"):
            env.run(until=5)

    def test_probabilities_never_given(self):
        _, d1, _ = _probabilistic_net(_fresh_env(), probabilities=None, seed=1)
        with pytest.raises(ValueError, match="probabilities"):
            d1.selection_policy.select(1)

    def test_set_probabilities_before_all_links(self):
        env = _fresh_env()
        sups = {i: scm.Supplier(env=env, ID=i, name=i, node_type="infinite_supplier") for i in ("S1", "S2", "S3")}
        d1 = scm.InventoryNode(env=env, ID="D1", name="D1", node_type="distributor", capacity=100,
                               initial_level=0, inventory_holding_cost=0, replenishment_policy=None,
                               policy_param=None, product_buy_price=1, product_sell_price=2,
                               supplier_selection_policy=scm.SelectProbabilistic)
        scm.Link(env=env, ID="L1", source=sups["S1"], sink=d1, cost=1, lead_time=lambda: 1)
        d1.selection_policy.set_probabilities(_PROBS)  # only L1 exists yet: no error
        scm.Link(env=env, ID="L2", source=sups["S2"], sink=d1, cost=1, lead_time=lambda: 1)
        scm.Link(env=env, ID="L3", source=sups["S3"], sink=d1, cost=1, lead_time=lambda: 1)
        assert d1.selection_policy.select(1).source.ID in _PROBS
        with pytest.raises(ValueError):
            d1.selection_policy.set_probabilities({"S1": 0.5, "S2": 0.6, "S3": 0.0})

    def test_set_probabilities_replaces_them(self):
        _, d1, (l1, l2, l3) = _probabilistic_net(_fresh_env(), seed=1)
        d1.selection_policy.select(1)
        d1.selection_policy.set_probabilities({"S1": 0.0, "S2": 0.0, "S3": 1.0})
        assert all(d1.selection_policy.select(1) is l3 for _ in range(50))

    def test_seed_none_means_no_seed(self):
        # A script may pass seed=cfg.get("seed") with no seed set: scm.set_seed must still repeat the run.
        def run():
            _, d1, _ = _probabilistic_net(_fresh_env(), seed=None)  # passed to the policy as seed: None
            return [d1.selection_policy.select(1).source.ID for _ in range(50)]
        scm.set_seed(3)
        first = run()
        scm.set_seed(3)
        assert run() == first

    def test_rng_none_means_no_rng(self):
        assert _sequence(seed=7, rng=None) == _sequence(seed=7)

    def test_numpy_integer_seed(self):
        np = pytest.importorskip("numpy")
        assert _sequence(seed=np.int64(7)) == _sequence(seed=7)

    def test_unusable_seed_rejected(self):
        with pytest.raises(ValueError, match="seed"):
            _probabilistic_net(_fresh_env(), seed=[1, 2])

    def test_info(self):
        _, d1, _ = _probabilistic_net(_fresh_env(), seed=1)
        info = d1.selection_policy.get_info()
        assert info["probabilities"] == _PROBS
        assert info["on_disruption"] == "rescale"


def _probabilistic_netlist(probabilities):
    """Dict netlist: S0 supplies D1, D2, D3; retailer R1 buys from all three with SelectProbabilistic."""
    site = {"node_type": "distributor", "capacity": 1000, "initial_level": 1000, "inventory_holding_cost": 0,
            "replenishment_policy": scm.SSReplenishment, "policy_param": {"s": 300, "S": 1000},
            "product_buy_price": 1, "product_sell_price": 2}
    nodes = [{"ID": "S0", "name": "S0", "node_type": "infinite_supplier"}]
    nodes += [dict(site, ID=d, name=d) for d in ("D1", "D2", "D3")]
    nodes.append(dict(site, ID="R1", name="R1", node_type="retailer", capacity=60, initial_level=60,
                      policy_param={"s": 20, "S": 60}, product_buy_price=2, product_sell_price=3,
                      supplier_selection_policy=scm.SelectProbabilistic,
                      supplier_selection_param={"probabilities": probabilities, "seed": 7}))
    links = [{"ID": f"L{d}", "source": "S0", "sink": d, "cost": 1, "lead_time": lambda: 2} for d in ("D1", "D2", "D3")]
    links += [{"ID": f"L{d}R1", "source": d, "sink": "R1", "cost": 1, "lead_time": lambda: 1}
              for d in ("D1", "D2", "D3")]
    demands = [{"ID": "C1", "name": "C1", "node_type": "demand", "order_arrival_model": lambda: 1,
                "order_quantity_model": lambda: 10, "demand_node": "R1"}]
    return nodes, links, demands


class TestSelectProbabilisticInNetworks(unittest.TestCase):
    """create_sc_net checks every site's probabilities against its links before the run."""

    def test_dict_style_runs_and_splits(self):
        sc = scm.create_sc_net(*_probabilistic_netlist({"D1": 0.5, "D2": 0.3, "D3": 0.2}))
        scm.simulate_sc_net(sc, 2000, logging=False)
        orders = {d: sc["links"][f"L{d}R1"].stats.demand_placed[0] for d in ("D1", "D2", "D3")}
        total = sum(orders.values())
        assert total > 300
        for d, p in zip(("D1", "D2", "D3"), (0.5, 0.3, 0.2)):
            assert abs(orders[d] / total - p) < 0.05, (d, orders)

    def test_missing_link_probability_fails_in_create_sc_net(self):
        with pytest.raises(ValueError, match="D3"):
            scm.create_sc_net(*_probabilistic_netlist({"D1": 0.5, "D2": 0.5}))

    def test_full_grid_with_zeros(self):
        sc = scm.create_sc_net(*_probabilistic_netlist({"D1": 1.0, "D2": 0.0, "D3": 0.0}))
        scm.simulate_sc_net(sc, 200, logging=False)
        assert sc["links"]["LD1R1"].stats.demand_placed[0] > 0
        assert sc["links"]["LD2R1"].stats.demand_placed == [0, 0]
        assert sc["links"]["LD3R1"].stats.demand_placed == [0, 0]

    def test_manufacturer_policy_not_checked(self):
        rm = scm.RawMaterial(ID="RM1", name="RM1", extraction_quantity=10, extraction_time=1, mining_cost=1, cost=1)
        prod = scm.Product(ID="P1", name="P1", manufacturing_cost=1, manufacturing_time=1, sell_price=5,
                           raw_materials=[(rm, 1)], batch_size=10)
        nodes = [{"ID": "S1", "name": "S1", "node_type": "infinite_supplier", "raw_material": rm},
                 {"ID": "M1", "name": "M1", "node_type": "manufacturer", "capacity": 50, "initial_level": 50,
                  "inventory_holding_cost": 0, "replenishment_policy": None, "policy_param": {},
                  "product": prod, "product_sell_price": 5,
                  "supplier_selection_policy": scm.SelectProbabilistic}]
        links = [{"ID": "L1", "source": "S1", "sink": "M1", "cost": 1, "lead_time": lambda: 1}]
        with pytest.warns(UserWarning, match="manufacturer does not use"):
            scm.create_sc_net(nodes, links, [{"ID": "C1", "name": "C1", "node_type": "demand",
                                              "order_arrival_model": lambda: 1, "order_quantity_model": lambda: 1,
                                              "demand_node": "M1"}])


class TestSelectionPolicyDefaultMode(unittest.TestCase):
    # A site passes no mode when none is given, so each policy's own default
    # applies. Every policy before SelectProbabilistic defaults to "fixed".
    def test_every_policy_defaults_to_fixed(self):
        node = DummyNode(env=_fresh_env())
        for policy in (scm.SelectFirst, scm.SelectAvailable, scm.SelectCheapest, scm.SelectFastest):
            assert policy(node).mode == "fixed", policy.__name__


def _selection_site(env, **kw):
    return scm.InventoryNode(env=env, ID="D1", name="D1", node_type="distributor", capacity=100,
                             initial_level=0, inventory_holding_cost=0, replenishment_policy=None,
                             policy_param=None, product_buy_price=1, product_sell_price=2, **kw)


def _selection_manufacturer(env, **kw):
    rm = scm.RawMaterial(ID="RM1", name="RM1", extraction_quantity=10,
                         extraction_time=2, mining_cost=1, cost=2)
    prod = scm.Product(ID="P1", name="P1", manufacturing_cost=1, manufacturing_time=1, sell_price=20,
                       raw_materials=[(rm, 1)], batch_size=5)
    return scm.Manufacturer(env=env, ID="M1", name="M1", capacity=100, initial_level=10,
                            inventory_holding_cost=0, product_sell_price=20, replenishment_policy=None,
                            policy_param={}, product=prod, **kw)


class TestSelectionPolicySettings(unittest.TestCase):
    """
    A site passes supplier_selection_mode and supplier_selection_param to its
    supplier-selection policy only when they are given, so each policy keeps
    its own default mode.
    """

    def test_mode_left_out_gives_the_policy_default(self):
        for policy in (scm.SelectFirst, scm.SelectAvailable, scm.SelectCheapest, scm.SelectFastest):
            site = _selection_site(_fresh_env(), supplier_selection_policy=policy)
            assert site.selection_policy.mode == "fixed", policy.__name__

    def test_mode_given_is_passed_on(self):
        site = _selection_site(_fresh_env(), supplier_selection_policy=scm.SelectCheapest,
                               supplier_selection_mode="dynamic")
        assert site.selection_policy.mode == "dynamic"

    def test_custom_policy_without_init(self):
        class Custom(scm.SupplierSelectionPolicy):
            def select(self, order_quantity):
                return self._apply_mode(self._active_suppliers()[0])
        assert _selection_site(_fresh_env(), supplier_selection_policy=Custom).selection_policy.mode == "fixed"
        site = _selection_site(_fresh_env(), supplier_selection_policy=Custom, supplier_selection_mode="dynamic")
        assert site.selection_policy.mode == "dynamic"

    def test_custom_policy_with_init_and_mode_default(self):
        class Custom(scm.SupplierSelectionPolicy):
            def __init__(self, node, mode="fixed"):
                super().__init__(node, mode)
            def select(self, order_quantity):
                return self.node.suppliers[0]
        assert _selection_site(_fresh_env(), supplier_selection_policy=Custom).selection_policy.mode == "fixed"
        site = _selection_site(_fresh_env(), supplier_selection_policy=Custom, supplier_selection_mode="dynamic")
        assert site.selection_policy.mode == "dynamic"

    def test_unknown_param_for_a_built_in_policy_warns(self):
        with pytest.warns(UserWarning, match="supplier_selection_param"):
            _selection_site(_fresh_env(), supplier_selection_policy=scm.SelectFirst,
                            supplier_selection_param={"seed": 1})

    def test_warning_says_the_policy_takes_no_parameters(self):
        with pytest.warns(UserWarning, match="takes no parameters"):
            _selection_site(_fresh_env(), supplier_selection_policy=scm.SelectCheapest,
                            supplier_selection_param={"probabilities": {"S1": 1.0}})

    def test_empty_param_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _selection_site(_fresh_env(), supplier_selection_policy=scm.SelectFirst, supplier_selection_param={})

    def test_manufacturer_given_another_policy_warns(self):
        with pytest.warns(UserWarning, match="manufacturer does not use"):
            _selection_manufacturer(_fresh_env(), supplier_selection_policy=scm.SelectCheapest)

    def test_manufacturer_given_a_mode_warns(self):
        with pytest.warns(UserWarning, match="manufacturer does not use"):
            _selection_manufacturer(_fresh_env(), supplier_selection_mode="dynamic")

    def test_manufacturer_given_probabilistic_policy_with_settings_warns(self):
        with pytest.warns(UserWarning, match="manufacturer does not use"):
            _selection_manufacturer(_fresh_env(), supplier_selection_policy=scm.SelectProbabilistic,
                                    supplier_selection_param={"probabilities": {"S1": 1.0}, "seed": 1})

    def test_manufacturer_warns_before_its_policy_checks_settings(self):
        # Settings that are wrong are still an error, but the warning that the
        # policy is not used comes first, so the user sees why it does not matter.
        with pytest.warns(UserWarning, match="manufacturer does not use"):
            with pytest.raises(ValueError):
                _selection_manufacturer(_fresh_env(), supplier_selection_policy=scm.SelectProbabilistic,
                                        supplier_selection_param={"probabilities": {"S1": 0.4}})

    def test_unused_probabilistic_policy_on_manufacturer_draws_nothing(self):
        # The policy is ignored, so it must not move the library's random numbers:
        # a site created after the manufacturer gets the same seed either way.
        def later_draws(**manufacturer_kw):
            scm.set_seed(11)
            env = _fresh_env()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                _selection_manufacturer(env, **manufacturer_kw)
            site = _selection_site(env, supplier_selection_policy=scm.SelectProbabilistic)
            return [site.selection_policy.rng.random() for _ in range(5)]
        expected = later_draws()
        assert later_draws(supplier_selection_policy=scm.SelectProbabilistic) == expected
        assert later_draws(supplier_selection_policy=scm.SelectProbabilistic,
                           supplier_selection_param={"probabilities": {"S1": 1.0}, "seed": None}) == expected

    def test_unused_probabilistic_policy_on_manufacturer_keeps_user_settings(self):
        settings = {"probabilities": {"S1": 1.0}}
        with pytest.warns(UserWarning, match="manufacturer does not use"):
            m = _selection_manufacturer(_fresh_env(), supplier_selection_policy=scm.SelectProbabilistic,
                                        supplier_selection_param=settings)
        assert settings == {"probabilities": {"S1": 1.0}}  # the user's dict is not changed
        assert m.selection_policy.probabilities == {"S1": 1.0}

    def test_manufacturer_with_the_default_policy_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _selection_manufacturer(_fresh_env())
            _selection_manufacturer(_fresh_env(), supplier_selection_policy=scm.SelectFirst)

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

    def test_put_at_capacity_wall_does_not_crash(self):
        # Regression for the "Known bugs" float-overshoot crash (CLAUDE.md).
        # capacity=99.99 with this initial level is a pair where the
        # fill-to-capacity put makes SimPy's container _level round to one ULP
        # ABOVE capacity (99.99000000000001). The exact-equality "full" guard
        # then missed that state, and the *next* put recomputed a negative
        # fill-to-capacity amount and fed it to SimPy, raising
        # "amount(=-1.42e-14) must be > 0.". The fix must instead treat the
        # over-the-wall node as full and accept 0.
        inv = scm.Inventory(env=self.node.env, capacity=99.99, initial_level=17.29320252118375,
                            node=self.node, replenishment_policy=None, holding_cost=0.1)
        # Put #1: fills right onto the wall; container _level overshoots by 1 ULP.
        inv.put(82.69679747881625)
        self.assertGreaterEqual(inv.level, 99.99)
        # Put #2: used to crash. Must be a no-op that reports nothing accepted.
        accepted = inv.put(10)
        self.assertEqual(accepted, 0)

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

    def test_perishable_inventory_rejected(self):
        # Perishable raw materials are not modelled yet. A perishable inventory
        # used to be accepted here and fail only at the first mining.
        for node_type, extra in (("supplier", {'capacity': 100, 'initial_level': 50, 'raw_material': self.rawmat}),
                                 ("infinite_supplier", {})):
            for key in ("inventory_type", "inv_type"):
                with pytest.raises(ValueError, match="perishable raw materials"):
                    scm.Supplier(env=self.env, ID="S2", name="Supplier 2", node_type=node_type,
                                 **extra, **{key: "perishable", 'shelf_life': 5})

    def test_non_perishable_inventory_type_accepted(self):
        node = scm.Supplier(env=self.env, ID="S2", name="Supplier 2", node_type="supplier", capacity=100,
                            initial_level=50, raw_material=self.rawmat, inventory_type="non-perishable")
        self.env.run(until=5)
        assert node.inventory.inv_type == "non-perishable"

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
        # The clamp uses the inventory position, which subtracts the units owed
        # to waiting customers (see Node.position).
        src = inspect.getsource(scm.InventoryNode.process_order)
        assert "gross = self.position()" in src, \
            "§3.10 capacity clamp must use the backorder-aware inventory position"
        src2 = inspect.getsource(scm.Manufacturer.process_order)
        assert "gross = self.position()" in src2, \
            "§3.10 capacity clamp in Manufacturer must also use the inventory position"


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

    def test_disable_logging_closes_the_log_file(self):
        # The file handler must be closed, not only taken off the logger, or
        # the log file stays open (and locked on Windows) until the program ends.
        import os, tempfile
        from SupplyNetPy.Components.logger import GlobalLogger
        with tempfile.TemporaryDirectory() as folder:
            log = GlobalLogger(logger_name="test_close_on_disable",
                               log_file=os.path.join(folder, "trace.log"))
            log.enable_logging(log_to_file=True, log_to_screen=False)
            handler = self._file_handlers(log.logger)[0]
            log.disable_logging()
            assert handler.stream is None
            os.remove(os.path.join(folder, "trace.log"))  # fails on Windows if still open

    def test_switching_log_file_closes_the_old_one(self):
        import os, tempfile
        from SupplyNetPy.Components.logger import GlobalLogger
        with tempfile.TemporaryDirectory() as folder:
            log = GlobalLogger(logger_name="test_close_on_switch",
                               log_file=os.path.join(folder, "first.log"))
            log.enable_logging(log_to_file=True, log_to_screen=False)
            first = self._file_handlers(log.logger)[0]
            log.set_log_file(os.path.join(folder, "second.log"))
            assert first.stream is None
            assert self._file_handlers(log.logger)[0].baseFilename.endswith("second.log")
            log.disable_logging()


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
        with pytest.warns(FutureWarning, match="deprecated"):
            scm.simulate_sc_net(sc, sim_time=20, logging=(3, 7))
        assert sc["profit"] == -4435.0


def _scripted_seq(values, tail):
    """Zero-arg callable that yields ``values`` in order, then ``tail`` forever.

    ``Demand.__init__`` samples each of its callables twice before the
    simulation starts (once in ``ensure_numeric_callable``, once in the explicit
    ``validate_number`` line), so callers prepend two harmless padding values to
    ``values`` to absorb those construction-time samples.
    """
    seq = list(values)
    state = {"i": 0}

    def _next():
        i = state["i"]
        state["i"] += 1
        return seq[i] if i < len(seq) else tail

    return _next


class TestReplenishmentDropAndDiscard(unittest.TestCase):
    """Replenishment-shipment drop handling (CLAUDE.md drop-loop conventions).

    Two scenarios where an arriving replenishment shipment used to be dropped
    silently are addressed here:

    * **Scenario A** — a backordered customer's patience runs out and it leaves
      before the over-capacity shipment lands, so there is no one to hand the
      surplus to. The surplus is still legitimately dropped, but now a warning
      is logged flagging that the node's capacity may be too small.
    * **Scenario B** — a customer orders more than the node's whole shelf can
      hold and accepts no partial delivery, so it can never be served. That
      order is now discarded up front (recorded as lost demand, no backorder,
      no replenishment) instead of driving a doomed over-capacity order that
      would only be dropped on arrival.
    """

    def _build_distributor_net(self, env, lead_time, arrival_model,
                               quantity_model, tolerance, min_split=1.0):
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier")
        d1 = scm.InventoryNode(
            env=env, ID="D1", name="D1", node_type="distributor",
            capacity=100, initial_level=100, inventory_holding_cost=0.1,
            replenishment_policy=scm.SSReplenishment, policy_param={"s": 90, "S": 100},
            product_buy_price=10, product_sell_price=12,
        )
        link = scm.Link(env=env, ID="L1", source=s1, sink=d1, cost=1,
                        lead_time=lambda lt=lead_time: lt)
        dem = scm.Demand(
            env=env, ID="dem", name="dem", demand_node=d1,
            order_arrival_model=arrival_model, order_quantity_model=quantity_model,
            tolerance=tolerance, order_min_split_ratio=min_split,
        )
        return d1

    def test_scenario_a_drop_logs_capacity_warning(self):
        # A full shelf (100/100), a 60-unit sale then an 80-unit order whose
        # customer's tolerance (2 days) expires before the 5-day-lead shipment
        # lands. The order placed to cover that backorder arrives to a full
        # shelf with no one waiting -> surplus dropped, with a warning.
        scm.set_seed(42)
        env = simpy.Environment()
        d1 = self._build_distributor_net(
            env, lead_time=5,
            arrival_model=_scripted_seq([0, 0, 0, 1], tail=100),   # 2 padding + script
            quantity_model=_scripted_seq([1, 1, 60, 80], tail=1),  # 2 padding + script
            tolerance=2,
        )
        with self.assertLogs("sim_trace", level="WARNING") as cm:
            env.run(until=10)
        dropped_lines = [m for m in cm.output if "Dropped" in m and "D1" in m]
        assert dropped_lines, f"expected a drop warning, got: {cm.output}"
        assert any("capacity" in m for m in dropped_lines)
        # The shelf ends full and never overshoots its capacity.
        assert d1.inventory.level == d1.inventory.capacity

    def test_scenario_b_over_capacity_order_is_discarded(self):
        # One customer wants 130 units from a node whose shelf holds 100 and
        # who accepts no partial delivery: it can never be served. The order
        # must be discarded (recorded as lost demand) — no backorder, no
        # replenishment, and therefore no later drop.
        scm.set_seed(42)
        env = simpy.Environment()
        d1 = self._build_distributor_net(
            env, lead_time=3,
            # One customer at t=0 (wants 130), then the next arrival is pushed
            # past the run so no trailing customer touches the shelf.
            arrival_model=_scripted_seq([0, 0, 1000], tail=1000),
            quantity_model=_scripted_seq([1, 1, 130], tail=1),
            tolerance=1000, min_split=1.0,
        )
        with self.assertLogs("sim_trace", level="WARNING") as cm:
            env.run(until=8)
        stats = d1.stats.get_statistics()
        # No backorder was ever created for the unservable order.
        assert stats["backorder"] == [0, 0]
        # The node never placed a replenishment order off the back of it.
        assert stats["demand_placed"] == [0, 0]
        # The lost demand is recorded as a shortage and a warning was logged.
        assert stats["shortage"] == [1, 130]
        assert any("discarded" in m for m in cm.output)
        # Nothing was delivered, so the shelf is untouched (no drop).
        assert d1.inventory.level == 100

    def test_servable_partial_order_is_not_discarded(self):
        # Guard against over-eager discarding: an order larger than capacity is
        # still servable when partial delivery (min_split < 1) lets it arrive in
        # chunks the shelf can hold. Such an order must NOT be discarded — it
        # keeps its backorder and drives replenishment as before.
        scm.set_seed(42)
        env = simpy.Environment()
        d1 = self._build_distributor_net(
            env, lead_time=2,
            arrival_model=_scripted_seq([0, 0, 1000], tail=1000),
            quantity_model=_scripted_seq([1, 1, 130], tail=1),
            tolerance=1000, min_split=0.5,   # 65-unit chunks fit on a 100 shelf
        )
        # Stop before the shipment arrives (lead time 2): we only need to see
        # that the order was accepted into the system, not discarded.
        env.run(until=1)
        stats = d1.stats.get_statistics()
        # A backorder was created (the order was enqueued, not discarded), and
        # the node placed a replenishment order off the back of it.
        assert stats["backorder"][0] >= 1
        assert stats["demand_placed"][0] >= 1


class TestWaitingCustomerLeavesOnTime(unittest.TestCase):
    """Customers who are willing to wait (``tolerance > 0``).

    A waiting customer must leave as soon as their patience runs out, even if
    no new stock arrives, and what they were still owed must then be taken off
    the node's current backorders. Before this fix a customer only noticed
    that their patience had run out when stock next arrived, so a customer
    who had already given up stayed counted as a backorder (and kept the node
    reordering for them) until the next delivery, or forever if none came.
    """

    def _plain_site(self, env, initial_level=0):
        # A site with no reorder rule, so stock arrives only when the test adds it.
        return scm.InventoryNode(
            env=env, ID="W1", name="W1", node_type="warehouse",
            capacity=float("inf"), initial_level=initial_level,
            inventory_holding_cost=0, replenishment_policy=None, policy_param={},
            product_buy_price=1, product_sell_price=2,
        )

    def test_backorder_cleared_when_patience_runs_out_before_restock(self):
        # One customer wants 50 from a shelf of 10 and waits at most 5 days.
        # The restock takes 20 days, so the customer leaves on day 5.
        env = simpy.Environment()
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier")
        w1 = scm.InventoryNode(
            env=env, ID="W1", name="W1", node_type="warehouse",
            capacity=float("inf"), initial_level=10, inventory_holding_cost=0,
            replenishment_policy=scm.SSReplenishment, policy_param={"s": 5, "S": 10},
            product_buy_price=1, product_sell_price=2,
        )
        scm.Link(env=env, ID="L1", source=s1, sink=w1, cost=0, lead_time=lambda: 20)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                   order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 50,
                   tolerance=5)
        env.run(until=4.5)
        assert w1.stats.backorder == [1, 50]   # still waiting
        env.run(until=5.5)
        assert w1.stats.backorder == [0, 0]    # left on day 5, long before the restock
        assert w1.position() == w1.inventory.on_hand

    def test_backorder_cleared_when_no_stock_ever_arrives(self):
        env = simpy.Environment()
        w1 = self._plain_site(env)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                   order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 5,
                   tolerance=2)
        env.run(until=1.5)
        assert w1.stats.backorder == [1, 5]
        env.run(until=50)
        assert w1.stats.backorder == [0, 0]

    def test_customer_served_if_stock_arrives_in_time(self):
        env = simpy.Environment()
        w1 = self._plain_site(env)
        dem = scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                         order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 5,
                         tolerance=10)
        env.run(until=3)
        w1.inventory.put(5)
        env.run(until=20)
        assert dem.stats.fulfillment_received == [1, 5]
        assert w1.stats.backorder == [0, 0]

    def test_endless_patience_keeps_waiting(self):
        env = simpy.Environment()
        w1 = self._plain_site(env)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                   order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 5,
                   tolerance=float("inf"))
        env.run(until=500)
        assert w1.stats.backorder == [1, 5]

    def test_all_waiting_customers_are_woken(self):
        # Three customers (5 units each) wait at a site with an empty shelf.
        # A delivery of 3 serves no one; a later delivery of 12 must still
        # reach all three, including those who started waiting first.
        env = simpy.Environment()
        w1 = self._plain_site(env)
        arrivals = _scripted_seq([0, 0, 0.1, 0.1], tail=1e9)   # 2 padding + script
        dem = scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                         order_arrival_model=arrivals, order_quantity_model=lambda: 5,
                         tolerance=100)
        env.run(until=1)
        assert w1.stats.backorder == [3, 15]
        w1.inventory.put(3)
        env.run(until=2)
        w1.inventory.put(12)
        env.run(until=20)
        assert dem.stats.fulfillment_received[1] == 15
        assert w1.stats.backorder == [0, 0]


class TestWaitingCustomerShortageCountedOnce(unittest.TestCase):
    """A waiting customer's shortage is recorded once, when the order arrives.

    The shortage was recorded when the order arrived, and then again each time
    the waiting customer checked and could not be served: twice at once, and
    once more after every delivery that was not enough. One customer short by
    10 units showed a shortage of [2, 20] straight away, and more later.
    """

    def _site(self, env):
        # A site with no stock and no replenishment policy: units arrive only
        # when the test adds them.
        return scm.InventoryNode(
            env=env, ID="W1", name="W1", node_type="warehouse",
            capacity=float("inf"), initial_level=0,
            inventory_holding_cost=0, replenishment_policy=None, policy_param={},
            product_buy_price=1, product_sell_price=2,
        )

    def _deliver(self, env, site, day, qty):
        yield env.timeout(day)
        site.inventory.put(qty)

    def test_shortage_recorded_once_while_deliveries_are_too_small(self):
        # One customer orders 10 and waits; three deliveries (2, 3, 4) are
        # each too small to fill the order.
        env = simpy.Environment()
        w1 = self._site(env)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                   order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 10,
                   tolerance=10)
        for day, qty in ((1, 2), (2, 3), (3, 4)):
            env.process(self._deliver(env, w1, day, qty))
        env.run(until=0.5)
        assert w1.stats.shortage == [1, 10]
        env.run(until=5)
        assert w1.stats.shortage == [1, 10]
        assert w1.stats.backorder == [1, 10]   # still waiting for all 10
        env.run(until=20)
        assert w1.stats.shortage == [1, 10]    # never reduced, never added to
        assert w1.stats.backorder == [0, 0]    # left when the tolerance ran out

    def test_shortage_recorded_once_with_partial_deliveries(self):
        # The customer accepts partial deliveries of 2 or more, so the
        # deliveries are passed on as they come.
        env = simpy.Environment()
        w1 = self._site(env)
        dem = scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                         order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 10,
                         tolerance=10, order_min_split_ratio=0.2)
        for day, qty in ((1, 2), (2, 3), (3, 4)):
            env.process(self._deliver(env, w1, day, qty))
        env.run(until=5)
        assert w1.stats.shortage == [1, 10]
        assert dem.stats.fulfillment_received[1] == 9   # 2 + 3 + 4 delivered
        assert w1.stats.backorder == [1, 1]             # 1 unit still owed

    def test_one_shortage_per_waiting_customer(self):
        # Three customers (5 units each) wait at a site with no stock.
        env = simpy.Environment()
        w1 = self._site(env)
        arrivals = _scripted_seq([0, 0, 0.1, 0.1], tail=1e9)   # 2 padding + script
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                   order_arrival_model=arrivals, order_quantity_model=lambda: 5,
                   tolerance=100)
        env.process(self._deliver(env, w1, 1, 3))   # too small for anyone
        env.run(until=5)
        assert w1.stats.shortage == [3, 15]


class TestCustomersOnlyTakeFreeStock(unittest.TestCase):
    """Customers must only be promised units that are really free for them.

    Two ways this used to go wrong:

    * Several waiting customers woken by the same delivery all checked the
      shelf before any of them had taken anything, so they all saw the same
      units and all thought those units were theirs. The extra customers were
      taken off the backorders but then sat in the shelf's queue of waiting
      requests, where their patience no longer applied.
    * Units on the shelf that are already promised to an earlier request
      still waiting in the queue (for example, a site's order the shelf
      cannot fill yet) were counted as free. Requests are served strictly in
      order, so a customer who asked for them would wait behind that request.

    Also covers a small order whose minimum partial delivery rounds down to
    0 units, which used to crash by asking the shelf for 0 units.
    """

    def _plain_site(self, env, initial_level=0):
        # A site with no reorder rule, so stock arrives only when the test adds it.
        return scm.InventoryNode(
            env=env, ID="W1", name="W1", node_type="warehouse",
            capacity=float("inf"), initial_level=initial_level,
            inventory_holding_cost=0, replenishment_policy=None, policy_param={},
            product_buy_price=1, product_sell_price=2,
        )

    def test_waiting_customers_do_not_claim_the_same_stock(self):
        # Three customers (5 units each) with endless patience wait at an
        # empty site. 5 units arrive: only one customer can be served.
        env = simpy.Environment()
        w1 = self._plain_site(env)
        arrivals = _scripted_seq([0, 0, 0.1, 0.1], tail=1e9)   # 2 padding + script
        dem = scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                         order_arrival_model=arrivals, order_quantity_model=lambda: 5,
                         tolerance=float("inf"))
        env.run(until=1)
        assert w1.stats.backorder == [3, 15]
        w1.inventory.put(5)
        env.run(until=50)
        assert dem.stats.fulfillment_received == [1, 5]
        assert w1.stats.backorder == [2, 10]               # two customers still waiting
        assert len(w1.inventory.inventory.get_queue) == 0  # and not stuck in the shelf's queue

    def test_restock_shared_among_several_waiting_customers(self):
        # Six customers (5 units each) with endless patience arrive at an
        # empty warehouse during days 0 to 1.5. The warehouse's reorder rule
        # brings 20 units on day 5: enough for four of them. Those four are
        # served, and the other two keep waiting for the next delivery.
        env = simpy.Environment()
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier")
        w1 = scm.InventoryNode(
            env=env, ID="W1", name="W1", node_type="warehouse",
            capacity=float("inf"), initial_level=0, inventory_holding_cost=0,
            replenishment_policy=scm.SSReplenishment, policy_param={"s": 0, "S": 20},
            product_buy_price=1, product_sell_price=2,
        )
        scm.Link(env=env, ID="L1", source=s1, sink=w1, cost=0, lead_time=lambda: 5)
        arrivals = _scripted_seq([0, 0, 0.3, 0.3, 0.3, 0.3, 0.3], tail=1e9)   # 2 padding + script
        dem = scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                         order_arrival_model=arrivals, order_quantity_model=lambda: 5,
                         tolerance=float("inf"))
        env.run(until=4.9)
        assert w1.stats.backorder == [6, 30]
        env.run(until=5.1)
        assert w1.stats.backorder == [2, 10]               # four served, two still waiting
        assert len(w1.inventory.inventory.get_queue) == 0  # nobody stuck in the shelf's queue
        env.run(until=30)
        assert dem.stats.fulfillment_received == [6, 30]
        assert w1.stats.backorder == [0, 0]

    def test_customer_without_patience_skips_stock_promised_to_a_queued_request(self):
        # An earlier request for 50 waits at the front of the queue while the
        # shelf holds 10. A customer who will not wait wants 5: nothing is
        # free for them, so they leave as a shortage instead of joining the queue.
        env = simpy.Environment()
        w1 = self._plain_site(env, initial_level=10)
        w1.inventory.get(50)
        dem = scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                         order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 5)
        env.run(until=1)
        assert w1.stats.shortage == [1, 5]
        assert dem.stats.fulfillment_received == [0, 0]
        assert [request.amount for request in w1.inventory.inventory.get_queue] == [50]

    def test_waiting_customer_leaves_at_tolerance_behind_a_queued_request(self):
        # An earlier request for 10 waits at an empty shelf. A customer wants
        # 5 and waits at most 2 days. 5 units arrive on day 1, but they belong
        # to the earlier request, so the customer leaves on day 2 without them.
        env = simpy.Environment()
        w1 = self._plain_site(env)
        w1.inventory.get(10)
        dem = scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                         order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 5,
                         tolerance=2)
        env.run(until=1)
        w1.inventory.put(5)
        env.run(until=5)
        assert w1.stats.backorder == [0, 0]
        w1.inventory.put(10)
        env.run(until=6)
        assert dem.stats.fulfillment_received == [0, 0]   # the customer had already left

    def test_partial_delivery_rounding_to_zero_does_not_crash(self):
        # An order of 1 with a minimum partial delivery of half rounds down
        # to 0 units. With an empty shelf, the customer must just wait and
        # then leave, not ask the shelf for 0 units.
        env = simpy.Environment()
        w1 = self._plain_site(env)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                   order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 1,
                   tolerance=5, order_min_split_ratio=0.5)
        env.run(until=10)
        assert w1.stats.backorder == [0, 0]


class TestSiteBackordersAreLive(unittest.TestCase):
    """A site's backorders show the orders from other sites it owes right now.

    When a warehouse orders from a distributor that cannot fill the order
    right away, the order waits at the distributor and counts as one of its
    backorders. Once the distributor sends it, it must stop counting. Before
    this fix the backorder was added but never removed, so the distributor
    seemed to owe the order for the rest of the run. Shortage is different:
    it records what could not be sent right away, and stays recorded.
    """

    def _site(self, env, ID, initial_level):
        # A site with no reorder rule, so stock arrives only when the test adds it.
        return scm.InventoryNode(
            env=env, ID=ID, name=ID, node_type="warehouse",
            capacity=float("inf"), initial_level=initial_level,
            inventory_holding_cost=0, replenishment_policy=None, policy_param={},
            product_buy_price=1, product_sell_price=2,
        )

    def _distributor_and_warehouse(self, env, distributor_stock):
        d1 = self._site(env, "D1", distributor_stock)
        w1 = self._site(env, "W1", 0)
        link = scm.Link(env=env, ID="L1", source=d1, sink=w1, cost=0, lead_time=lambda: 2)
        return d1, w1, link

    def test_backorder_cleared_once_the_order_is_sent(self):
        # The warehouse orders 50 from a distributor holding 10. The order
        # waits until 40 more units reach the distributor on day 3.
        env = simpy.Environment()
        d1, w1, link = self._distributor_and_warehouse(env, distributor_stock=10)
        env.process(w1.process_order(link, 50))
        env.run(until=1)
        assert d1.stats.backorder == [1, 50]   # owed while it waits
        assert d1.stats.shortage == [1, 40]
        env.run(until=3)
        d1.inventory.put(40)
        env.run(until=10)
        assert d1.stats.backorder == [0, 0]    # sent, so no longer owed
        assert d1.stats.shortage == [1, 40]    # the shortage stays recorded
        assert w1.inventory.level == 50

    def test_order_sent_right_away_is_never_a_backorder(self):
        env = simpy.Environment()
        d1, w1, link = self._distributor_and_warehouse(env, distributor_stock=100)
        env.process(w1.process_order(link, 50))
        env.run(until=1)
        assert d1.stats.backorder == [0, 0]
        env.run(until=10)
        assert d1.stats.backorder == [0, 0]
        assert w1.inventory.level == 50

    def test_order_waiting_behind_an_earlier_request_is_a_backorder(self):
        # The distributor's 10 units are promised to an earlier request for
        # 50 that is still waiting. The warehouse's order for 5 waits behind
        # it, even though 10 units sit on the shelf.
        env = simpy.Environment()
        d1, w1, link = self._distributor_and_warehouse(env, distributor_stock=10)
        d1.inventory.get(50)
        env.process(w1.process_order(link, 5))
        env.run(until=1)
        assert d1.stats.backorder == [1, 5]
        d1.inventory.put(45)                   # enough for both requests
        env.run(until=10)
        assert d1.stats.backorder == [0, 0]
        assert w1.inventory.level == 5

    def test_disrupted_distributor_records_no_backorder(self):
        # A disrupted distributor takes no order, so it owes nothing.
        env = simpy.Environment()
        d1, w1, link = self._distributor_and_warehouse(env, distributor_stock=10)
        d1.node_status = "inactive"
        w1.place_order(50)
        env.run(until=10)
        assert d1.stats.backorder == [0, 0]
        assert w1.pending_orders == 0

    def test_waiting_site_order_counted_once_in_position(self):
        # The distributor holds 10 and owes the warehouse 50. Its position is
        # 10 - 50 = -40. The order was already taken off on_hand when it was
        # placed, so it must not be subtracted a second time (-90).
        env = simpy.Environment()
        d1, w1, link = self._distributor_and_warehouse(env, distributor_stock=10)
        env.process(w1.process_order(link, 50))
        env.run(until=1)
        assert d1.inventory.waiting_orders() == 50
        assert d1.position() == -40

    def test_waiting_customer_still_counted_in_position(self):
        # A customer waiting for stock was not taken off on_hand, so the
        # position must subtract them.
        env = simpy.Environment()
        w1 = self._site(env, "W1", 0)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                   order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 5,
                   tolerance=float("inf"))
        env.run(until=1)
        assert w1.inventory.waiting_orders() == 0
        assert w1.position() == -5

    def test_expired_goods_removed_at_once_not_behind_a_site_order(self):
        # Perishable goods that last 2 days. The distributor holds 10 and owes
        # the warehouse 50. On day 1, 20 more units arrive. All 30 expire (on
        # days 2 and 3) while the warehouse's order is still waiting. They are
        # thrown away at once, not queued behind that order, so only the
        # order waits in line and only it is owed to a site.
        env = simpy.Environment()
        def perishable_site(ID, initial_level):
            return scm.InventoryNode(
                env=env, ID=ID, name=ID, node_type="warehouse",
                capacity=float("inf"), initial_level=initial_level,
                inventory_holding_cost=0, replenishment_policy=None, policy_param={},
                product_buy_price=1, product_sell_price=2,
                inventory_type="perishable", shelf_life=2,
            )
        d1, w1 = perishable_site("D1", 10), perishable_site("W1", 0)
        link = scm.Link(env=env, ID="L1", source=d1, sink=w1, cost=0, lead_time=lambda: 2)
        env.process(w1.process_order(link, 50))
        env.run(until=1)
        d1.inventory.put(20, 1)                # made on day 1
        env.run(until=3.5)
        assert d1.inventory.level == 0                   # the expired units are gone
        assert d1.inventory.waste == 30
        assert d1.inventory.waiting_orders() == 50       # only the order waits in line
        assert d1.inventory.waiting_site_orders() == 50
        assert d1.stats.backorder == [1, 50]
        assert d1.position() == d1.inventory.on_hand     # no customers are waiting

    def test_distributor_reorders_only_what_it_owes(self):
        # Distributor (s=20, S=60) holds 60. The warehouse orders 100, so the
        # distributor's position drops to -40 and it orders 60 - (-40) = 100.
        # Counting the warehouse's order twice made it order 200 and then sit
        # on 100 extra units for the rest of the run.
        env = simpy.Environment()
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier")
        d1 = scm.InventoryNode(
            env=env, ID="D1", name="D1", node_type="distributor",
            capacity=float("inf"), initial_level=60, inventory_holding_cost=0,
            replenishment_policy=scm.SSReplenishment, policy_param={"s": 20, "S": 60},
            product_buy_price=1, product_sell_price=2,
        )
        scm.Link(env=env, ID="L1", source=s1, sink=d1, cost=0, lead_time=lambda: 2)
        w1 = self._site(env, "W1", 0)
        link = scm.Link(env=env, ID="L2", source=d1, sink=w1, cost=0, lead_time=lambda: 2)
        env.process(w1.process_order(link, 100))
        env.run(until=10)
        assert d1.stats.demand_placed == [1, 100]
        assert d1.inventory.level == 60        # back at S, nothing extra
        assert d1.stats.backorder == [0, 0]
        assert w1.inventory.level == 100


class TestFactoryMakesWhatItOwes(unittest.TestCase):
    """A factory must make the units it owes to sites waiting for its product.

    The factory works out how many units it still has to make from on_hand
    and its shelf. Orders from other sites that wait at its shelf have
    already been taken off on_hand, so they must be added back. Without that,
    a factory that receives an order bigger than its shelf decides there is
    nothing to make, and the order waits forever.
    """

    def test_factory_fills_an_order_bigger_than_its_shelf(self):
        # The factory (s=5, S=10) holds 10. The warehouse (s=40, S=50) starts
        # empty and orders 50. The factory buys 50 units of raw material,
        # makes 50, sends 50, and ends back at 10 with nothing left over.
        def raw_material():
            return scm.RawMaterial(ID="rm1", name="rm1", extraction_quantity=1,
                                   extraction_time=1, mining_cost=0, cost=1)
        product = scm.Product(ID="P", name="P", manufacturing_cost=1, manufacturing_time=1,
                              sell_price=5, buy_price=0, batch_size=1000,
                              raw_materials=[(raw_material(), 1)])
        net = scm.create_sc_net(
            nodes=[dict(ID="S1", name="S1", node_type="infinite_supplier", raw_material=raw_material()),
                   dict(ID="M1", name="M1", node_type="manufacturer", capacity=float("inf"),
                        initial_level=10, inventory_holding_cost=0,
                        replenishment_policy=scm.SSReplenishment,
                        policy_param=dict(s=5, S=10, period=1),
                        product_sell_price=5, product=product),
                   dict(ID="W1", name="W1", node_type="warehouse", capacity=float("inf"),
                        initial_level=0, inventory_holding_cost=0,
                        replenishment_policy=scm.SSReplenishment,
                        policy_param=dict(s=40, S=50, period=1),
                        product_buy_price=1, product_sell_price=2)],
            links=[dict(ID="l1", source="S1", sink="M1", cost=0, lead_time=lambda: 1),
                   dict(ID="l2", source="M1", sink="W1", cost=0, lead_time=lambda: 1)],
            demands=[dict(ID="d", name="d", demand_node="W1", order_arrival_model=lambda: 1e6,
                          order_quantity_model=lambda: 1, consume_available=True)])
        net["env"].run(until=200)
        m1, w1 = net["nodes"]["M1"], net["nodes"]["W1"]
        assert w1.stats.fulfillment_received[1] == 50
        assert m1.stats.demand_placed[1] == 50             # raw material bought
        assert m1.stats.total_products_manufactured == 50
        assert m1.raw_inventory_counts["rm1"] == 0         # nothing left over
        assert m1.inventory.level == 10
        assert m1.inventory.waiting_orders() == 0
        assert m1.stats.backorder == [0, 0]


class TestFactoryKeepsProducing(unittest.TestCase):
    """A factory keeps making batches until every planned unit is made.

    A batch makes at most `batch_size` units. The factory used to make one
    batch per raw-material delivery and then wait for the next delivery, so
    raw material for the rest of the plan sat unused and the factory could
    stop for good. Every planned unit must also have its raw material
    ordered: units planned without it can never be made, yet the factory
    counts on them and stops ordering.
    """

    def _factory(self, env, raw_materials=(("RM1", 1),), capacity=float("inf"), initial_level=0,
                 batch_size=5, manufacturing_time=1, lead_time=1, policy=None, policy_param=None):
        # One endless supplier per raw material, each on its own link.
        rawmats = [scm.RawMaterial(ID=rid, name=rid, extraction_quantity=1, extraction_time=1,
                                   mining_cost=0, cost=1) for rid, _ in raw_materials]
        product = scm.Product(ID="P", name="P", manufacturing_cost=1, manufacturing_time=manufacturing_time,
                              sell_price=5, buy_price=0, batch_size=batch_size,
                              raw_materials=[(rm, qty) for rm, (_, qty) in zip(rawmats, raw_materials)])
        m1 = scm.Manufacturer(env=env, ID="M1", name="M1", capacity=capacity, initial_level=initial_level,
                              inventory_holding_cost=0, replenishment_policy=policy, policy_param=policy_param,
                              product_sell_price=5, product=product)
        links = {}
        for rm in rawmats:
            sup = scm.Supplier(env=env, ID=f"S_{rm.ID}", name=f"S_{rm.ID}",
                               node_type="infinite_supplier", raw_material=rm)
            links[rm.ID] = scm.Link(env=env, ID=f"L_{rm.ID}", source=sup, sink=m1, cost=0,
                                    lead_time=lambda: lead_time)
        return m1, links

    def test_one_delivery_is_made_into_every_batch_it_covers(self):
        # The factory plans 25 units with a batch size of 5. The raw material
        # for all 25 arrives on day 1; batches finish on days 2, 3, 4, 5, 6.
        env = simpy.Environment()
        m1, links = self._factory(env)
        env.process(m1.process_order(links["RM1"], 25))
        env.run(until=2.5)
        assert m1.stats.total_products_manufactured == 5
        env.run(until=10)
        assert m1.stats.total_products_manufactured == 25
        assert m1.raw_inventory_counts["RM1"] == 0
        assert m1.stats.demand_placed == [1, 25]   # one delivery covered all five batches

    def test_raw_material_ordered_while_an_earlier_order_is_on_its_way(self):
        # Two plans, half a day apart. The raw material for the first is still
        # on its way when the second comes in, but the second gets its own order.
        env = simpy.Environment()
        m1, links = self._factory(env, lead_time=2, batch_size=100)
        env.process(m1.process_order(links["RM1"], 20))
        env.run(until=0.5)
        env.process(m1.process_order(links["RM1"], 30))
        env.run(until=10)
        assert m1.stats.demand_placed == [2, 50]
        assert m1.stats.total_products_manufactured == 50
        assert m1.raw_inventory_counts["RM1"] == 0

    def test_leftover_raw_material_does_not_cancel_a_new_order(self):
        # The factory plans 30 and slowly makes them, 5 per batch, 10 days per
        # batch. On day 2 it holds 25 units of raw material, all set aside for
        # the 25 units still to make. A new plan for 20 must still order 20.
        env = simpy.Environment()
        m1, links = self._factory(env, manufacturing_time=10)
        env.process(m1.process_order(links["RM1"], 30))
        env.run(until=2)
        assert m1.raw_inventory_counts["RM1"] == 25
        env.process(m1.process_order(links["RM1"], 20))
        env.run(until=200)
        assert m1.stats.demand_placed == [2, 50]
        assert m1.stats.total_products_manufactured == 50
        assert m1.raw_inventory_counts["RM1"] == 0

    def test_factory_carries_on_once_its_full_shelf_has_space(self):
        # The shelf is full (10 of 10), while 10 more units are planned and
        # their raw material is on hand. The factory waits; as stock leaves
        # the shelf, it carries on.
        env = simpy.Environment()
        m1, links = self._factory(env, capacity=10, initial_level=10)
        env.run(until=1)
        m1.inventory.on_hand += 10            # 10 more units planned...
        m1.raw_inventory_counts["RM1"] = 10   # ...and their raw material is here
        m1.wake_production()
        env.run(until=5)
        assert m1.stats.total_products_manufactured == 0   # no space
        m1.inventory.get(7)
        env.run(until=10)
        assert m1.stats.total_products_manufactured == 7   # filled the space that was freed
        assert m1.inventory.level == 10
        m1.inventory.get(10)
        env.run(until=15)
        assert m1.stats.total_products_manufactured == 10  # all planned units made
        assert m1.raw_inventory_counts["RM1"] == 0

    def test_disrupted_raw_material_link_plans_nothing(self):
        # The product needs flour and sugar. The sugar link is down until
        # day 5. While it is down, the factory plans nothing and orders
        # nothing (not even flour). Once it is back, the policy plans 40,
        # both raw materials are ordered, and all 40 are made.
        env = simpy.Environment()
        m1, links = self._factory(env, raw_materials=(("flour", 1), ("sugar", 2)), capacity=100,
                                  batch_size=50, policy=scm.SSReplenishment,
                                  policy_param={"s": 10, "S": 40, "period": 1})
        links["sugar"].status = "inactive"
        def repair():
            yield env.timeout(5)
            links["sugar"].status = "active"
        env.process(repair())
        env.run(until=4)
        assert m1.inventory.on_hand == 0
        assert m1.stats.demand_placed == [0, 0]
        assert links["flour"].source.stats.shortage == [0, 0]
        env.run(until=10)
        assert m1.stats.demand_placed == [2, 120]   # 40 flour + 80 sugar
        assert m1.stats.total_products_manufactured == 40
        assert m1.inventory.level == 40

    def test_raw_material_ordered_from_one_working_supplier(self):
        # Two suppliers sell the same raw material. The factory orders from
        # the first one only; when the first one's link is down, from the second.
        env = simpy.Environment()
        m1, links = self._factory(env, batch_size=100)
        rm = links["RM1"].source.raw_material
        second = scm.Supplier(env=env, ID="S2", name="S2", node_type="infinite_supplier", raw_material=rm)
        scm.Link(env=env, ID="L2", source=second, sink=m1, cost=0, lead_time=lambda: 1)
        first = links["RM1"].source
        env.process(m1.process_order(links["RM1"], 10))
        env.run(until=3)
        assert first.stats.demand_received == [1, 10]
        assert second.stats.demand_received == [0, 0]
        links["RM1"].status = "inactive"
        env.process(m1.process_order(links["RM1"], 10))
        env.run(until=6)
        assert first.stats.demand_received == [1, 10]
        assert second.stats.demand_received == [1, 10]
        assert m1.stats.total_products_manufactured == 20

    def test_reported_example_keeps_serving_customers(self):
        # The example from GitHub issue #1 (batch size 5, 300 days). The
        # factory used to make 10 units and stop for good on day 14, while
        # customers got 4% of what they asked for.
        rm = scm.RawMaterial(ID="rm1", name="rm1", extraction_quantity=1, extraction_time=1,
                             mining_cost=0, cost=1)
        bread = scm.Product(ID="P", name="P", manufacturing_cost=1, manufacturing_time=1, sell_price=5,
                            buy_price=0, batch_size=5, raw_materials=[(rm, 1)])
        net = scm.create_sc_net(
            nodes=[dict(ID="S1", name="S1", node_type="infinite_supplier", raw_material=rm),
                   dict(ID="M1", name="M1", node_type="manufacturer", capacity=float("inf"),
                        initial_level=30, inventory_holding_cost=0,
                        replenishment_policy=scm.SSReplenishment,
                        policy_param=dict(s=20, S=40, period=1), product_sell_price=5, product=bread),
                   dict(ID="W1", name="W1", node_type="warehouse", capacity=float("inf"),
                        initial_level=0, inventory_holding_cost=0,
                        replenishment_policy=scm.SSReplenishment,
                        policy_param=dict(s=10, S=15, period=1),
                        product_buy_price=1, product_sell_price=2)],
            links=[dict(ID="l1", source="S1", sink="M1", cost=0, lead_time=lambda: 1),
                   dict(ID="l2", source="M1", sink="W1", cost=0, lead_time=lambda: 1)],
            demands=[dict(ID="d", name="d", demand_node="W1", order_arrival_model=lambda: 1,
                          order_quantity_model=lambda: 3, consume_available=True)])
        net["env"].run(until=300)
        m1, d = net["nodes"]["M1"], net["demands"]["d"]
        assert m1.stats.total_products_manufactured > 850
        assert d.stats.fulfillment_received[1] / d.stats.demand_placed[1] > 0.95
        assert m1.raw_inventory_counts["rm1"] < 5   # no raw material left sitting unused


# The buyers here have no capacity limit, on purpose, so creating their links
# warns that they could order more than the supplier holds (§3.27). The
# orders these tests place all fit the supplier.
@pytest.mark.filterwarnings("ignore:Supplier S1 can hold at most")
class TestLimitedSupplierKeepsMining(unittest.TestCase):
    """A supplier with a limited shelf mines again as soon as a buyer takes stock.

    A supplier mines until its shelf is full and then waits for the "stock
    went down" signal. That signal used to reach only nodes with a
    replenishment policy, which suppliers never have, so a supplier whose
    shelf had once been full never mined again.
    """

    def _supplier(self, env, capacity=20, initial_level=20):
        # Mines 5 units a day, up to a shelf of `capacity`.
        rm = scm.RawMaterial(ID="RM1", name="RM1", extraction_quantity=5, extraction_time=1,
                             mining_cost=0, cost=1)
        sup = scm.Supplier(env=env, ID="S1", name="S1", node_type="supplier", capacity=capacity,
                           initial_level=initial_level, raw_material=rm)
        return sup, rm

    def _distributor(self, env, ID="D1"):
        return scm.InventoryNode(env=env, ID=ID, name=ID, node_type="distributor", capacity=float("inf"),
                                 initial_level=0, inventory_holding_cost=0, replenishment_policy=None,
                                 policy_param=None, product_sell_price=5, product_buy_price=1)

    def _order_at(self, env, day, buyer, link, qty):
        yield env.timeout(day)
        yield env.process(buyer.process_order(link, qty))

    def test_supplier_refills_its_shelf_after_a_sale(self):
        # A full supplier sells 10 units on day 0, then mines 5 a day until
        # its shelf is full again.
        env = simpy.Environment()
        sup, _ = self._supplier(env)
        d1 = self._distributor(env)
        link = scm.Link(env=env, ID="L1", source=sup, sink=d1, cost=0, lead_time=lambda: 1)
        env.process(d1.process_order(link, 10))
        env.run(until=5)
        assert sup.inventory.level == 20
        assert sup.stats.total_raw_materials_mined == 10

    def test_orders_smaller_than_the_shelf_find_it_full_again(self):
        # Orders of 10 every 5 days never ask for more than the supplier has,
        # so no order wakes it by running short. It must refill after each one.
        env = simpy.Environment()
        sup, _ = self._supplier(env)
        d1 = self._distributor(env)
        link = scm.Link(env=env, ID="L1", source=sup, sink=d1, cost=0, lead_time=lambda: 1)
        for day in (0, 5, 10):
            env.process(self._order_at(env, day, d1, link, 10))
        for day in (4.5, 9.5, 14.5):
            env.run(until=day)
            assert sup.inventory.level == 20   # full again before the next order
        assert d1.inventory.level == 30         # every order arrived after one day
        assert sup.stats.backorder == [0, 0]    # no order ever had to wait

    def test_factory_gets_raw_material_from_a_supplier_that_was_full(self):
        # A factory buys all 20 units on day 0, and 20 more on day 10. The
        # supplier must mine again so the second order is filled.
        env = simpy.Environment()
        sup, rm = self._supplier(env)
        product = scm.Product(ID="P", name="P", manufacturing_cost=1, manufacturing_time=1, sell_price=5,
                              buy_price=0, batch_size=5, raw_materials=[(rm, 1)])
        m1 = scm.Manufacturer(env=env, ID="M1", name="M1", capacity=float("inf"), initial_level=0,
                              inventory_holding_cost=0, replenishment_policy=None, policy_param=None,
                              product_sell_price=5, product=product)
        link = scm.Link(env=env, ID="L1", source=sup, sink=m1, cost=0, lead_time=lambda: 1)
        env.process(self._order_at(env, 0, m1, link, 20))
        env.process(self._order_at(env, 10, m1, link, 20))
        env.run(until=40)
        assert m1.stats.total_products_manufactured == 40
        assert sup.inventory.waiting_orders() == 0
        assert sup.stats.backorder == [0, 0]
        assert sup.inventory.level == 20   # and it has refilled its shelf since

    def test_disrupted_supplier_site_is_not_told_stock_went_down(self):
        # The supplying site is down, so the order is not placed. Nothing
        # leaves its shelf, so its "stock went down" signal must not fire
        # (that would make its own policy reorder for no reason).
        env = simpy.Environment()
        w0 = self._distributor(env, ID="W0")
        d1 = self._distributor(env)
        link = scm.Link(env=env, ID="L1", source=w0, sink=d1, cost=0, lead_time=lambda: 1)
        w0.node_status = "inactive"
        d1.place_order(10)
        env.run(until=1)
        assert not w0.inventory_drop.triggered
        assert d1.pending_orders == 0


class TestNoShortageAtASupplierSiteThatIsDown(unittest.TestCase):
    """A supplier is counted as short only for orders it really receives.

    When the supplying site is down, the order is not placed. The supplier
    used to be counted as short for it anyway, before the code checked
    whether its site was up.
    """

    def _warehouse_and_distributor(self, env):
        # W0 has 5 units; D1 will order 20 from it.
        w0 = scm.InventoryNode(env=env, ID="W0", name="W0", node_type="warehouse", capacity=100,
                               initial_level=5, inventory_holding_cost=0, replenishment_policy=None,
                               policy_param=None, product_sell_price=5, product_buy_price=1)
        d1 = scm.InventoryNode(env=env, ID="D1", name="D1", node_type="distributor", capacity=100,
                               initial_level=0, inventory_holding_cost=0, replenishment_policy=None,
                               policy_param=None, product_sell_price=5, product_buy_price=1)
        link = scm.Link(env=env, ID="L1", source=w0, sink=d1, cost=0, lead_time=lambda: 1)
        return w0, d1, link

    def test_supplier_site_down_is_not_counted_as_short(self):
        env = simpy.Environment()
        w0, d1, link = self._warehouse_and_distributor(env)
        w0.node_status = "inactive"
        for _ in range(3):   # the policy may try several times during an outage
            d1.place_order(20)
        env.run(until=1)
        assert w0.stats.shortage == [0, 0]
        assert w0.stats.demand_received == [0, 0]
        assert w0.stats.backorder == [0, 0]
        assert d1.stats.demand_placed == [0, 0]
        assert d1.pending_orders == 0

    def test_supplier_site_up_is_still_counted_as_short(self):
        # The same order to a working site that is short: counted as before.
        env = simpy.Environment()
        w0, d1, link = self._warehouse_and_distributor(env)
        env.process(d1.process_order(link, 20))
        env.run(until=1)
        assert w0.stats.shortage == [1, 15]
        assert w0.stats.demand_received == [1, 20]


class TestPerishableBatchesPickedWhenShipped(unittest.TestCase):
    """Dated batches are picked when units leave the shelf, oldest first.

    The dates used to be picked when an order was *placed*. An order that had
    to wait got dates for only the units on the shelf at that moment, so the
    buyer received fewer units than it paid for, the old units' expiry was
    missed and they were shipped already expired. Expired goods and destroyed
    stock also waited in line behind orders instead of leaving at once.
    """

    def _site(self, env, ID, level, shelf_life=10):
        return scm.InventoryNode(env=env, ID=ID, name=ID, node_type="warehouse", capacity=100,
                                 initial_level=level, inventory_holding_cost=0, replenishment_policy=None,
                                 policy_param=None, product_sell_price=5, product_buy_price=1,
                                 inventory_type="perishable", shelf_life=shelf_life)

    def _deliver(self, env, site, day, qty):
        # Stock arriving at `site` on `day`, made that day.
        yield env.timeout(day)
        site.inventory.put(qty, env.now)
        site.inventory.on_hand += qty

    def _batches(self, site):
        # The dated batches, oldest first, leaving out empty ones (a site that
        # starts with no stock holds an empty batch until its expiry check
        # clears it).
        return sorted(b for b in site.inventory.perish_queue if b[1] > 0)

    def _records_agree(self, site):
        return sum(q for _, q in site.inventory.perish_queue) == site.inventory.level

    def test_waiting_order_gets_every_unit_with_its_real_dates(self):
        # W0 has 5 units (made on day 0); D1 orders 20. On day 2, 30 fresh
        # units arrive and the order is served: 5 old units and 15 new ones.
        env = simpy.Environment()
        w0, d1 = self._site(env, "W0", 5), self._site(env, "D1", 0)
        link = scm.Link(env=env, ID="L1", source=w0, sink=d1, cost=0, lead_time=lambda: 1)
        env.process(d1.process_order(link, 20))
        env.process(self._deliver(env, w0, 2, 30))
        env.run(until=5)
        assert d1.stats.fulfillment_received == [1, 20]
        assert d1.inventory.level == 20
        assert self._batches(d1) == [(0, 5), (2, 15)]
        assert w0.inventory.level == 15
        assert self._batches(w0) == [(2, 15)]
        assert self._records_agree(w0) and self._records_agree(d1)

    def test_stock_that_expires_while_an_order_waits_is_not_shipped(self):
        # W0's 5 units (made on day 0) expire on day 3, while D1's order for
        # 20 waits. W0 throws them away; the order gets fresh units on day 4.
        env = simpy.Environment()
        w0, d1 = self._site(env, "W0", 5, shelf_life=3), self._site(env, "D1", 0, shelf_life=3)
        link = scm.Link(env=env, ID="L1", source=w0, sink=d1, cost=0, lead_time=lambda: 0.5)
        env.process(d1.process_order(link, 20))
        env.process(self._deliver(env, w0, 4, 30))
        env.run(until=3.5)
        assert w0.inventory.waste == 5
        assert w0.inventory.level == 0
        assert w0.inventory.waiting_orders() == 20       # the order still waits
        env.run(until=6)
        assert d1.stats.fulfillment_received == [1, 20]
        assert self._batches(d1) == [(4, 20)]
        assert d1.inventory.waste == 0
        assert w0.inventory.level == 10
        assert self._records_agree(w0) and self._records_agree(d1)

    def test_destroy_empties_the_shelf_at_once_while_an_order_waits(self):
        # D1's order for 20 waits at W0 (which has 5). Destroying W0's stock
        # removes the 5 units at once; the next delivery goes to the order.
        env = simpy.Environment()
        w0, d1 = self._site(env, "W0", 5), self._site(env, "D1", 0)
        link = scm.Link(env=env, ID="L1", source=w0, sink=d1, cost=0, lead_time=lambda: 1)
        env.process(d1.process_order(link, 20))
        env.run(until=1)
        assert w0.inventory.destroy() == 5
        assert w0.inventory.level == 0
        assert self._batches(w0) == []
        env.process(self._deliver(env, w0, 1, 30))       # day 2
        env.run(until=4)
        assert d1.stats.fulfillment_received == [1, 20]
        assert self._batches(d1) == [(2, 20)]
        assert w0.inventory.level == 10
        assert self._records_agree(w0)

    def test_destroy_restarts_a_full_supplier(self):
        # A supplier mines only when its shelf is not full. After its full
        # shelf is destroyed, it must start mining again.
        env = simpy.Environment()
        rm = scm.RawMaterial(ID="RM1", name="RM1", extraction_quantity=5, extraction_time=1,
                             mining_cost=0, cost=1)
        sup = scm.Supplier(env=env, ID="S1", name="S1", node_type="supplier", capacity=20,
                           initial_level=20, raw_material=rm)
        env.run(until=1)
        sup.inventory.destroy()
        env.run(until=5)
        assert sup.inventory.level == 20
        assert sup.stats.total_raw_materials_mined == 20

    def test_records_agree_in_a_busy_network(self):
        # A perishable chain with a reorder rule, customers and expiry. At
        # every check, the dated batches add up to the units on each shelf.
        env = simpy.Environment()
        sup = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier")
        sites = {}
        for ID, src in (("W1", sup), ("R1", None)):
            sites[ID] = scm.InventoryNode(
                env=env, ID=ID, name=ID, node_type="warehouse", capacity=200, initial_level=50,
                inventory_holding_cost=0, replenishment_policy=scm.SSReplenishment,
                policy_param={"s": 40, "S": 120}, product_sell_price=5, product_buy_price=1,
                inventory_type="perishable", shelf_life=6)
        scm.Link(env=env, ID="L1", source=sup, sink=sites["W1"], cost=0, lead_time=lambda: 2)
        scm.Link(env=env, ID="L2", source=sites["W1"], sink=sites["R1"], cost=0, lead_time=lambda: 1)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=sites["R1"],
                   order_arrival_model=lambda: 0.5, order_quantity_model=lambda: 7)
        for day in range(1, 60):
            env.run(until=day + 0.5)
            for site in sites.values():
                assert self._records_agree(site), (day, site.ID)
        assert sites["R1"].stats.demand_fulfilled[1] > 0
        assert sites["W1"].inventory.waste + sites["R1"].inventory.waste > 0   # expiry did happen


class TestSupplierRawMaterialBackordersAreLive(unittest.TestCase):
    """A raw-material supplier's backorders show the orders it owes right now.

    Same rule as for orders between sites (see TestSiteBackordersAreLive):
    a factory's raw-material order counts as a backorder at the supplier
    while it waits for stock, and stops counting once it is sent.
    """

    def _supplier_and_factory(self, env, cost=0):
        # The supplier starts empty and extracts 10 units a day, the first
        # 10 on day 0. The factory has no reorder rule, so the test places
        # the order itself.
        rawmat = scm.RawMaterial(ID="RM1", name="RM1", extraction_quantity=10,
                                 extraction_time=1, mining_cost=0, cost=1)
        product = scm.Product(ID="P1", name="P1", manufacturing_cost=1, manufacturing_time=1,
                              raw_materials=[(rawmat, 1)], sell_price=5, buy_price=0, batch_size=100)
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="supplier", capacity=100,
                          initial_level=0, inventory_holding_cost=0, raw_material=rawmat)
        m1 = scm.Manufacturer(env=env, ID="M1", name="M1", capacity=100, initial_level=0,
                              inventory_holding_cost=0, replenishment_policy=None, policy_param=None,
                              product_sell_price=5, product=product)
        link = scm.Link(env=env, ID="L1", source=s1, sink=m1, cost=cost, lead_time=lambda: 1)
        return s1, m1, link

    def test_raw_material_order_recorded_when_placed(self):
        # The factory's order is counted as placed (with its transportation
        # cost) when it is placed on day 0.5, as for every other site, not
        # only once the supplier has the units on day 2.
        env = simpy.Environment()
        s1, m1, link = self._supplier_and_factory(env, cost=4)
        env.run(until=0.5)
        env.process(m1.process_order_raw("RM1", link, 30))
        env.run(until=1.5)
        assert s1.stats.backorder == [1, 30]   # still waiting at the supplier
        assert m1.stats.demand_placed == [1, 30]
        assert m1.stats.transportation_cost == 4
        env.run(until=5)
        assert m1.stats.demand_placed == [1, 30]   # counted once
        assert m1.stats.transportation_cost == 4

    def test_backorder_cleared_once_the_raw_material_is_sent(self):
        # On day 0.5 the factory orders 30 while the supplier holds 10. The
        # supplier has 30 by day 2, sends the order, and it arrives on day 3.
        env = simpy.Environment()
        s1, m1, link = self._supplier_and_factory(env)
        env.run(until=0.5)
        env.process(m1.process_order_raw("RM1", link, 30))
        env.run(until=1.5)
        assert s1.stats.backorder == [1, 30]   # owed while it waits
        assert s1.stats.shortage == [1, 20]
        env.run(until=5)
        assert s1.stats.backorder == [0, 0]    # sent, so no longer owed
        assert s1.stats.shortage == [1, 20]    # the shortage stays recorded
        assert m1.raw_inventory_counts["RM1"] == 30

    def test_disrupted_supplier_records_no_backorder(self):
        # The factory checks that its suppliers are working before it plans
        # anything, so a disrupted supplier gets no order at all: no
        # backorder, no shortage, and nothing added to the factory's plan.
        env = simpy.Environment()
        s1, m1, link = self._supplier_and_factory(env)
        env.run(until=0.5)
        s1.node_status = "inactive"
        m1.place_order(30)
        env.run(until=5)
        assert s1.stats.backorder == [0, 0]
        assert s1.stats.shortage == [0, 0]
        assert s1.stats.demand_received == [0, 0]
        assert m1.inventory.on_hand == 0


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


class _StubRng:
    """Deterministic RNG stub. Records ``.random()`` call count and returns
    a fixed value (or values from a sequence). Used to pin the behavior of
    probabilistic disruption to a known schedule.
    """

    def __init__(self, value=None, seq=None):
        self.calls = 0
        self._value = value
        self._seq = list(seq) if seq is not None else None

    def random(self):
        self.calls += 1
        if self._seq is not None:
            if not self._seq:
                # Pad with the last value rather than raising — keeps the
                # disruption loop running so the test can observe steady
                # state past the scripted prefix.
                return 0.999
            return self._seq.pop(0)
        return self._value


class TestNodeDisruptionProbabilisticIsTimePaced(unittest.TestCase):
    """Regression: ``Node.disruption`` with only ``failure_p`` set must poll
    once per simulation tick.

    The earlier code only yielded ``timeout(1)`` after a *successful*
    disruption draw — a missed draw fell through ``while True`` with no
    ``yield``, busy-spinning in real wall time and drawing the rng
    unboundedly per tick. ``failure_p`` therefore collapsed to "near-certain
    disruption at t=0" regardless of its magnitude.

    With the fix in place, the rng is drawn exactly once per tick and the
    loop yields ``timeout(1)`` whether or not the draw hit, so ``failure_p``
    behaves as a per-tick probability.
    """

    def test_misses_do_not_busy_spin_and_node_stays_active(self):
        # rng always returns 0.99 — strictly above failure_p=0.01, so no
        # disruption ever fires. Without the fix this would tight-loop
        # forever (env.run never returns); with the fix env.run completes
        # and the rng is drawn once per tick.
        env = _fresh_env()
        rng = _StubRng(value=0.99)
        node = scm.InventoryNode(
            env=env, ID="D1", name="D1", node_type="warehouse",
            capacity=100, initial_level=80, inventory_holding_cost=0,
            replenishment_policy=None, policy_param={},
            product_sell_price=10, product_buy_price=5,
            failure_p=0.01, node_recovery_time=lambda: 3,
            rng=rng,
        )
        env.run(until=20)
        # One draw per tick, t=0..t=19 → 20 draws. No busy spin.
        assert rng.calls == 20
        assert node.node_status == "active"

    def test_hit_after_misses_flips_status_at_the_hitting_tick(self):
        # First two draws miss (0.9 > 0.01), third draw hits (0.001 < 0.01).
        # Schedule (with the fix):
        #   t=0: draw 0.9   → miss, yield 1
        #   t=1: draw 0.9   → miss, yield 1
        #   t=2: draw 0.001 → HIT, set inactive, yield 1
        #   t=3: status=inactive → wait recovery (10), so still inactive at t=12
        env = _fresh_env()
        rng = _StubRng(seq=[0.9, 0.9, 0.001])
        node = scm.InventoryNode(
            env=env, ID="D1", name="D1", node_type="warehouse",
            capacity=100, initial_level=80, inventory_holding_cost=0,
            replenishment_policy=None, policy_param={},
            product_sell_price=10, product_buy_price=5,
            failure_p=0.01, node_recovery_time=lambda: 10,
            rng=rng,
        )
        env.run(until=2)  # processes t=0 and t=1 (both misses), pauses pre-t=2
        assert node.node_status == "active"
        env.run(until=3)  # t=2 fires: draw 0.001 hits, status flips
        assert node.node_status == "inactive"


class TestLinkDisruptionProbabilisticIsTimePaced(unittest.TestCase):
    """Regression mirror of the Node test: ``Link.disruption`` with only
    ``link_failure_p`` set must poll once per simulation tick. Same
    underlying bug, same fix, same shape of regression test.
    """

    def _build_link(self, env, rng, failure_p):
        # Minimal source→sink topology. The link itself owns the disruption
        # process; the nodes' own disruption loops stay dormant because
        # neither failure_p nor disrupt_time is set on them.
        sup = scm.Supplier(
            env=env, ID="S1", name="S1", node_type="supplier",
            capacity=100, initial_level=100, inventory_holding_cost=0,
            raw_material=scm.RawMaterial(
                ID="R1", name="R1", cost=1,
                extraction_quantity=10, extraction_time=1, mining_cost=1,
            ),
        )
        snk = scm.InventoryNode(
            env=env, ID="D1", name="D1", node_type="warehouse",
            capacity=100, initial_level=50, inventory_holding_cost=0,
            replenishment_policy=None, policy_param={},
            product_sell_price=10, product_buy_price=5,
        )
        return scm.Link(
            env=env, ID="L1", source=sup, sink=snk,
            cost=0, lead_time=lambda: 1,
            link_failure_p=failure_p, link_recovery_time=lambda: 3,
            rng=rng,
        )

    def test_misses_do_not_busy_spin_and_link_stays_active(self):
        env = _fresh_env()
        rng = _StubRng(value=0.99)
        link = self._build_link(env, rng, failure_p=0.01)
        env.run(until=20)
        assert rng.calls == 20
        assert link.status == "active"

    def test_hit_after_misses_flips_status_at_the_hitting_tick(self):
        env = _fresh_env()
        rng = _StubRng(seq=[0.9, 0.9, 0.001])
        link = self._build_link(env, rng, failure_p=0.01)
        env.run(until=2)
        assert link.status == "active"
        env.run(until=3)
        assert link.status == "inactive"


class TestPolicyWokenWhenSupplierRecovers(unittest.TestCase):
    """
    A replenishment policy without a review period checks its inventory
    position only when it is woken, normally when its inventory drops. An
    order it tries to place while its supplier (or the link to it) is
    disrupted is not placed. If the node then has no units left, nothing can
    leave its inventory, so nothing would wake the policy again: the node
    would never order again, even after the supplier recovered. The supplier
    or link now wakes the buyer's policy when it recovers.
    """

    def _distributor(self, env, supplier_kwargs=None, link_kwargs=None):
        # The distributor holds 20 units and sells 10 a day to customers who
        # do not wait. It runs out on day 1 and wants to order then.
        sup = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier",
                           **(supplier_kwargs or {}))
        d1 = scm.InventoryNode(env=env, ID="D1", name="D1", node_type="distributor",
                               capacity=100, initial_level=20, inventory_holding_cost=0,
                               replenishment_policy=scm.SSReplenishment,
                               policy_param={"s": 5, "S": 20},
                               product_buy_price=1, product_sell_price=2)
        link = scm.Link(env=env, ID="L1", source=sup, sink=d1, cost=0, lead_time=lambda: 1,
                        **(link_kwargs or {}))
        scm.Demand(env=env, ID="C1", name="C1", order_arrival_model=lambda: 1,
                   order_quantity_model=lambda: 10, demand_node=d1)
        return sup, d1, link

    def test_buyer_orders_once_its_supplier_site_recovers(self):
        # The supplier is disrupted from day 0.5 to day 5.5. The distributor's
        # order on day 1 is not placed. When the supplier recovers on day 5.5,
        # the distributor orders 20 units at once.
        env = simpy.Environment()
        sup, d1, link = self._distributor(env, supplier_kwargs={
            "node_disrupt_time": lambda: 0.5, "node_recovery_time": lambda: 5})
        env.run(until=5)
        assert d1.inventory.level == 0
        assert d1.stats.demand_placed == [0, 0]
        env.run(until=5.75)
        assert d1.stats.demand_placed == [1, 20]
        env.run(until=7)
        assert d1.stats.fulfillment_received == [1, 20]

    def test_buyer_orders_once_its_link_recovers(self):
        # The same, with the link disrupted instead of the supplier.
        env = simpy.Environment()
        sup, d1, link = self._distributor(env, link_kwargs={
            "link_disrupt_time": lambda: 0.5, "link_recovery_time": lambda: 5})
        env.run(until=5)
        assert d1.stats.demand_placed == [0, 0]
        env.run(until=5.75)
        assert d1.stats.demand_placed == [1, 20]

    def test_manufacturer_plans_once_its_raw_material_supplier_recovers(self):
        # A manufacturer with no units and no review period wants to plan 40
        # units on day 0, but its raw-material supplier is disrupted from day
        # 0 (the start) to day 3. It plans and orders once the supplier is back.
        env = simpy.Environment()
        rm = scm.RawMaterial(ID="RM1", name="RM1", extraction_quantity=1, extraction_time=1,
                             mining_cost=0, cost=1)
        product = scm.Product(ID="P", name="P", manufacturing_cost=1, manufacturing_time=1,
                              sell_price=5, buy_price=0, batch_size=100, raw_materials=[(rm, 1)])
        sup = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier",
                           raw_material=rm, node_disrupt_time=lambda: 0.1,
                           node_recovery_time=lambda: 3)
        m1 = scm.Manufacturer(env=env, ID="M1", name="M1", capacity=100, initial_level=0,
                              inventory_holding_cost=0, replenishment_policy=scm.SSReplenishment,
                              policy_param={"s": 10, "S": 40, "first_review_delay": 1},
                              product_sell_price=5, product=product)
        scm.Link(env=env, ID="L1", source=sup, sink=m1, cost=0, lead_time=lambda: 1)
        env.run(until=3)
        assert m1.stats.demand_placed == [0, 0]
        env.run(until=6)
        assert m1.stats.demand_placed == [1, 40]
        assert m1.stats.total_products_manufactured == 40

    def test_link_is_registered_with_its_source(self):
        env = simpy.Environment()
        sup, d1, link = self._distributor(env)
        assert sup.buyers == [link]
        assert d1.buyers == []


class TestOrdersSkipDisruptedSupplierSites(unittest.TestCase):
    """
    place_order checks that some supplier can take the order, and the
    supplier-selection policy chooses only among suppliers whose link and
    site are both not disrupted. If none can take it, no order is placed.
    """

    def _two_suppliers(self, env, policy=scm.SelectFirst, mode="dynamic"):
        # D1 buys from S1 (first in the list, cheaper) and S2.
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier")
        s2 = scm.Supplier(env=env, ID="S2", name="S2", node_type="infinite_supplier")
        d1 = scm.InventoryNode(env=env, ID="D1", name="D1", node_type="distributor",
                               capacity=100, initial_level=0, inventory_holding_cost=0,
                               replenishment_policy=None, policy_param=None,
                               supplier_selection_policy=policy, supplier_selection_mode=mode,
                               product_buy_price=1, product_sell_price=2)
        l1 = scm.Link(env=env, ID="L1", source=s1, sink=d1, cost=1, lead_time=lambda: 1)
        l2 = scm.Link(env=env, ID="L2", source=s2, sink=d1, cost=5, lead_time=lambda: 1)
        return s1, s2, d1, l1, l2

    def test_order_goes_to_the_supplier_whose_site_is_not_disrupted(self):
        env = simpy.Environment()
        s1, s2, d1, l1, l2 = self._two_suppliers(env)
        s1.node_status = "inactive"
        d1.place_order(10)
        env.run(until=2)
        assert s1.stats.demand_received == [0, 0]
        assert s2.stats.demand_received == [1, 10]
        assert d1.stats.fulfillment_received == [1, 10]

    def test_fixed_mode_skips_its_supplier_while_the_site_is_disrupted(self):
        env = simpy.Environment()
        s1, s2, d1, l1, l2 = self._two_suppliers(env, policy=scm.SelectCheapest, mode="fixed")
        assert d1.selection_policy.select(10) is l1
        s1.node_status = "inactive"
        assert d1.selection_policy.select(10) is l2
        assert d1.selection_policy.fixed_supplier is l1, "the remembered supplier stays"
        s1.node_status = "active"
        assert d1.selection_policy.select(10) is l1

    def test_no_order_when_every_supplier_is_disrupted(self):
        # S1's site and the link to S2 are both disrupted: nothing is placed,
        # and nothing is counted anywhere.
        env = simpy.Environment()
        s1, s2, d1, l1, l2 = self._two_suppliers(env)
        s1.node_status = "inactive"
        l2.status = "inactive"
        assert not d1.can_place_order()
        d1.place_order(10)
        env.run(until=2)
        assert s1.stats.demand_received == [0, 0]
        assert s2.stats.demand_received == [0, 0]
        assert d1.stats.demand_placed == [0, 0]
        assert d1.pending_orders == 0

    def test_manufacturer_needs_a_supplier_for_every_raw_material(self):
        # Flour can be ordered, sugar cannot: the manufacturer cannot place
        # an order, because the units could never be made.
        env = simpy.Environment()
        flour = scm.RawMaterial(ID="flour", name="flour", extraction_quantity=1, extraction_time=1,
                                mining_cost=0, cost=1)
        sugar = scm.RawMaterial(ID="sugar", name="sugar", extraction_quantity=1, extraction_time=1,
                                mining_cost=0, cost=1)
        product = scm.Product(ID="P", name="P", manufacturing_cost=1, manufacturing_time=1,
                              sell_price=5, buy_price=0, batch_size=10,
                              raw_materials=[(flour, 1), (sugar, 1)])
        s_flour = scm.Supplier(env=env, ID="SF", name="SF", node_type="infinite_supplier", raw_material=flour)
        s_sugar = scm.Supplier(env=env, ID="SS", name="SS", node_type="infinite_supplier", raw_material=sugar)
        m1 = scm.Manufacturer(env=env, ID="M1", name="M1", capacity=100, initial_level=0,
                              inventory_holding_cost=0, replenishment_policy=None, policy_param=None,
                              product_sell_price=5, product=product)
        scm.Link(env=env, ID="LF", source=s_flour, sink=m1, cost=0, lead_time=lambda: 1)
        scm.Link(env=env, ID="LS", source=s_sugar, sink=m1, cost=0, lead_time=lambda: 1)
        s_sugar.node_status = "inactive"
        assert not m1.can_place_order()
        m1.place_order(10)
        env.run(until=2)
        assert m1.inventory.on_hand == 0
        assert s_flour.stats.demand_received == [0, 0]
        s_sugar.node_status = "active"
        assert m1.can_place_order()

    def _orders_at_time_zero(self, env, supplier_kwargs=None, link_kwargs=None):
        # D1 is created first and starts empty, so its policy orders at time 0,
        # before the random disruption of S1 or L1 makes its first draw.
        d1 = scm.InventoryNode(env=env, ID="D1", name="D1", node_type="distributor",
                               capacity=100, initial_level=0, inventory_holding_cost=0,
                               replenishment_policy=scm.SSReplenishment,
                               policy_param={"s": 5, "S": 20},
                               product_buy_price=1, product_sell_price=2)
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier",
                          **(supplier_kwargs or {}))
        link = scm.Link(env=env, ID="L1", source=s1, sink=d1, cost=0, lead_time=lambda: 1,
                        **(link_kwargs or {}))
        return d1, s1, link

    def test_link_disrupted_at_time_zero_after_place_order_gets_no_order(self):
        # place_order finds L1 active, but L1's first draw (0.13 < 0.99)
        # disrupts it before process_order runs. The order is not placed.
        env = simpy.Environment()
        d1, s1, link = self._orders_at_time_zero(env, link_kwargs={
            "link_failure_p": 0.99, "link_recovery_time": lambda: 100, "rng": random.Random(1)})
        env.run(until=0.5)
        assert link.status == "inactive"
        assert s1.stats.demand_received == [0, 0]
        assert d1.stats.demand_placed == [0, 0]
        assert d1.pending_orders == 0

    def test_site_disrupted_at_time_zero_after_place_order_gets_no_order(self):
        # The same, with S1's site disrupted instead of the link.
        env = simpy.Environment()
        d1, s1, link = self._orders_at_time_zero(env, supplier_kwargs={
            "failure_p": 0.99, "node_recovery_time": lambda: 100, "rng": random.Random(1)})
        env.run(until=0.5)
        assert s1.node_status == "inactive"
        assert s1.stats.demand_received == [0, 0]
        assert d1.stats.demand_placed == [0, 0]
        assert d1.pending_orders == 0


class TestUnusedPolicyParams(unittest.TestCase):
    """A replenishment policy warns about keys in policy_param that it does not use,
    and asks whether another policy was meant."""

    def _node(self, policy, params):
        env = simpy.Environment()
        return scm.InventoryNode(env=env, ID="D1", name="D1", node_type="distributor", capacity=100,
                                 initial_level=50, inventory_holding_cost=0, replenishment_policy=policy,
                                 policy_param=params, product_buy_price=1, product_sell_price=2)

    def test_ss_policy_warns_about_a_key_it_does_not_use(self):
        with pytest.warns(UserWarning, match=r"SSReplenishment does not use the parameter\(s\) 'T'.*another replenishment policy"):
            self._node(scm.SSReplenishment, {"s": 10, "S": 50, "T": 1})

    def test_rq_policy_names_every_unused_key(self):
        with pytest.warns(UserWarning, match=r"RQReplenishment does not use the parameter\(s\) 'S', 's'"):
            self._node(scm.RQReplenishment, {"R": 10, "Q": 40, "s": 10, "S": 50})

    def test_periodic_policy_warns_about_period(self):
        # The periodic policy reads T, not period.
        with pytest.warns(UserWarning, match=r"PeriodicReplenishment does not use the parameter\(s\) 'period'"):
            self._node(scm.PeriodicReplenishment, {"T": 1, "Q": 10, "period": 1})

    def test_no_warning_for_keys_the_policy_uses(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            self._node(scm.SSReplenishment, {"s": 10, "S": 50, "safety_stock": 5, "period": 1, "first_review_delay": 2})
            self._node(scm.RQReplenishment, {"R": 10, "Q": 40, "period": 1, "first_review_delay": 2})
            self._node(scm.PeriodicReplenishment, {"T": 1, "Q": 10, "safety_stock": 5, "first_review_delay": 2})

    def test_custom_policy_without_a_key_list_is_not_checked(self):
        import warnings

        class MyPolicy(scm.InventoryReplenishment):
            def run(self):
                yield self.env.timeout(1)

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            self._node(MyPolicy, {"anything": 1})


class TestSetupWarnings(unittest.TestCase):
    """Problems in how a model is set up are shown with Python's warnings, so the
    user sees them even when the library's logging is off."""

    def test_update_stats_warns_about_an_unknown_statistic(self):
        env = simpy.Environment()
        d1 = scm.InventoryNode(env=env, ID="D1", name="D1", node_type="distributor", capacity=100,
                               initial_level=50, inventory_holding_cost=0, replenishment_policy=None,
                               policy_param=None, product_buy_price=1, product_sell_price=2)
        with pytest.warns(UserWarning, match="unknown statistic 'no_such_stat'"):
            d1.stats.update_stats(no_such_stat=1)

    def test_manufacturer_without_a_supplier_for_every_raw_material_warns(self):
        env = simpy.Environment()
        flour = scm.RawMaterial(ID="flour", name="flour", extraction_quantity=1, extraction_time=1,
                                mining_cost=0, cost=1)
        sugar = scm.RawMaterial(ID="sugar", name="sugar", extraction_quantity=1, extraction_time=1,
                                mining_cost=0, cost=1)
        product = scm.Product(ID="P", name="P", manufacturing_cost=1, manufacturing_time=1, sell_price=5,
                              buy_price=0, batch_size=10, raw_materials=[(flour, 1), (sugar, 1)])
        s_flour = scm.Supplier(env=env, ID="SF", name="SF", node_type="infinite_supplier", raw_material=flour)
        m1 = scm.Manufacturer(env=env, ID="M1", name="M1", capacity=100, initial_level=0,
                              inventory_holding_cost=0, replenishment_policy=None, policy_param=None,
                              product_sell_price=5, product=product)
        scm.Link(env=env, ID="LF", source=s_flour, sink=m1, cost=0, lead_time=lambda: 1)
        with pytest.warns(UserWarning, match="Manufacturer M1 .* fewer suppliers"):
            env.run(until=1)


class TestStatisticsResetKeepsThePresent(unittest.TestCase):
    """``Statistics.reset()`` starts the counting again (for a warm-up) without
    changing values that describe the present (§3.24).

    A warm-up runs for a while, resets the statistics and carries on. The
    simulation itself carries on unchanged, so orders still waiting must stay
    counted as backorders, the holding cost must start from the reset, and the
    inventory level must still be read correctly.
    """

    def _site(self, env, initial_level=0, holding_cost=0, **kwargs):
        # A site with no replenishment policy: units arrive only when the test adds them.
        return scm.InventoryNode(
            env=env, ID="W1", name="W1", node_type="warehouse",
            capacity=float("inf"), initial_level=initial_level,
            inventory_holding_cost=holding_cost, replenishment_policy=None, policy_param={},
            product_buy_price=1, product_sell_price=2, **kwargs,
        )

    def _deliver(self, env, site, day, qty):
        yield env.timeout(day)
        site.inventory.put(qty)

    def test_waiting_customer_stays_a_backorder_through_a_reset(self):
        # A customer orders 10 at a site with no units and waits. The reset at
        # day 1 must not forget them: the backorder and the inventory position
        # stay as they were, and serving the customer at day 2 brings the
        # backorder back to [0, 0], not below.
        env = simpy.Environment()
        w1 = self._site(env)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                   order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 10,
                   tolerance=100)
        env.process(self._deliver(env, w1, 2, 10))
        env.run(until=1)
        position_before = w1.position()
        w1.stats.reset()
        assert w1.stats.backorder == [1, 10]
        assert w1.position() == position_before
        env.run(until=3)
        assert w1.stats.backorder == [0, 0]

    def test_holding_cost_after_a_reset_covers_only_the_time_since(self):
        # 10 units held at a cost of 1 per unit per time unit. The run stops at
        # day 5 with env.run (not simulate_sc_net), so the holding cost was
        # last brought up to date at day 0. After the reset, days 5 to 8 cost 30.
        env = simpy.Environment()
        w1 = self._site(env, initial_level=10, holding_cost=1)
        env.run(until=5)
        w1.stats.reset()
        env.run(until=8)
        w1.stats.update_stats()
        assert w1.stats.inventory_carry_cost == 30

    def test_inventory_level_is_read_again_on_reset(self):
        env = simpy.Environment()
        w1 = self._site(env, initial_level=10)
        env.run(until=1)
        w1.stats.reset()
        assert w1.stats.inventory_level == 10

    def test_recorded_inventory_levels_start_again_after_a_reset(self):
        # The once-per-time-unit record of the inventory level must not keep
        # samples from before the reset, or averages built from it would
        # include the warm-up.
        env = simpy.Environment()
        w1 = self._site(env, initial_level=10, record_inv_levels=True)
        env.run(until=5)
        assert len(w1.inventory.instantaneous_levels) > 0
        w1.stats.reset()
        assert w1.inventory.instantaneous_levels == []
        env.run(until=8)
        assert w1.inventory.instantaneous_levels
        assert all(t >= 5 for t, _ in w1.inventory.instantaneous_levels)

    def test_infinite_supplier_can_be_reset(self):
        # An infinite supplier's inventory level is infinite, so its holding
        # cost is never worked out; a reset must not try either.
        env = simpy.Environment()
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier")
        env.run(until=5)
        s1.stats.reset()
        s1.stats.update_stats()
        assert s1.stats.inventory_carry_cost == 0
        assert s1.stats.node_cost == 0


class TestCustomersCannotOrderFromADisruptedSite(unittest.TestCase):
    """While a site is disrupted it takes no new orders, from other sites or
    from customers (§3.26). A customer who arrives then is a sale the site
    loses because of the disruption: it is recorded as ``disruption_lost_sales``
    at the site, and not as demand received, shortage or backorder.
    """

    def _site(self, env, initial_level=50):
        # A site with no replenishment policy: units arrive only when the test adds them.
        return scm.InventoryNode(
            env=env, ID="W1", name="W1", node_type="retailer",
            capacity=float("inf"), initial_level=initial_level,
            inventory_holding_cost=0, replenishment_policy=None, policy_param={},
            product_buy_price=1, product_sell_price=2,
        )

    def _recover(self, env, site, day):
        yield env.timeout(day)
        site.node_status = "active"

    def _deliver(self, env, site, day, qty):
        yield env.timeout(day)
        site.inventory.put(qty)

    def test_customer_at_a_disrupted_site_is_a_lost_sale(self):
        # The site has 50 units, but it is disrupted when a customer orders 10.
        env = simpy.Environment()
        w1 = self._site(env)
        dem = scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                         order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 10)
        w1.node_status = "inactive"
        env.run(until=1)
        assert w1.stats.disruption_lost_sales == [1, 10]
        assert w1.stats.demand_received == [0, 0]
        assert w1.stats.shortage == [0, 0]
        assert w1.stats.backorder == [0, 0]
        assert w1.stats.demand_fulfilled == [0, 0]
        assert dem.stats.demand_placed == [0, 0]
        assert dem.stats.fulfillment_received == [0, 0]
        assert w1.inventory.level == 50

    def test_customers_are_served_again_after_recovery(self):
        # One customer a day; the site is disrupted until day 2.
        env = simpy.Environment()
        w1 = self._site(env)
        dem = scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                         order_arrival_model=lambda: 1, order_quantity_model=lambda: 10)
        w1.node_status = "inactive"
        env.process(self._recover(env, w1, 1.5))
        env.run(until=4.5)   # customers at days 0, 1 (lost), 2, 3, 4 (served)
        assert w1.stats.disruption_lost_sales == [2, 20]
        assert w1.stats.demand_received == [3, 30]
        assert dem.stats.fulfillment_received == [3, 30]

    def test_customer_already_waiting_is_still_served(self):
        # A customer starts waiting for 10 units at day 0; the site is
        # disrupted at day 1 and the units arrive at day 2. The customer's
        # order was taken before the disruption, so it is still served.
        env = simpy.Environment()
        w1 = self._site(env, initial_level=0)
        dem = scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                         order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 10,
                         tolerance=100)
        def disrupt():
            yield env.timeout(1)
            w1.node_status = "inactive"
        env.process(disrupt())
        env.process(self._deliver(env, w1, 2, 10))
        env.run(until=3)
        assert w1.stats.backorder == [0, 0]
        assert dem.stats.fulfillment_received == [1, 10]
        assert w1.stats.disruption_lost_sales == [0, 0]

    def test_every_kind_of_customer_is_turned_away(self):
        # Customers with no tolerance, customers who would wait, and customers
        # who take what is there are all turned away the same way.
        for kwargs in ({}, {"tolerance": 5}, {"consume_available": True}):
            env = simpy.Environment()
            w1 = self._site(env, initial_level=3)
            scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                       order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 10, **kwargs)
            w1.node_status = "inactive"
            env.run(until=1)
            assert w1.stats.disruption_lost_sales == [1, 10], kwargs
            assert w1.stats.shortage == [0, 0], kwargs
            assert w1.stats.backorder == [0, 0], kwargs
            assert w1.inventory.level == 3, kwargs

    def test_disruption_lost_sales_is_reported_and_reset(self):
        env = simpy.Environment()
        w1 = self._site(env)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                   order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 10)
        w1.node_status = "inactive"
        env.run(until=1)
        assert w1.stats.get_statistics()["disruption_lost_sales"] == [1, 10]
        w1.stats.reset()
        assert w1.stats.disruption_lost_sales == [0, 0]


class TestMoreNodeStatistics(unittest.TestCase):
    """Node statistics for disruptions, the inventory level over time, orders
    that end badly, and a clock for averages (§6.9)."""

    def _site(self, env, ID="W1", initial_level=0, capacity=float("inf"), **kwargs):
        # A site with no replenishment policy: units arrive only when the test adds them.
        return scm.InventoryNode(
            env=env, ID=ID, name=ID, node_type="retailer",
            capacity=capacity, initial_level=initial_level,
            inventory_holding_cost=0, replenishment_policy=None, policy_param={},
            product_buy_price=1, product_sell_price=2, **kwargs,
        )

    def _at(self, env, day, action):
        yield env.timeout(day)
        action()

    def _factory(self, env):
        rawmat = scm.RawMaterial(ID="RM1", name="RM1", extraction_quantity=10,
                                 extraction_time=1, mining_cost=0, cost=1)
        product = scm.Product(ID="P1", name="P1", manufacturing_cost=1, manufacturing_time=1,
                              raw_materials=[(rawmat, 1)], sell_price=5, buy_price=0, batch_size=100)
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="supplier", capacity=100,
                          initial_level=0, inventory_holding_cost=0, raw_material=rawmat)
        m1 = scm.Manufacturer(env=env, ID="M1", name="M1", capacity=100, initial_level=0,
                              inventory_holding_cost=0, replenishment_policy=None, policy_param=None,
                              product_sell_price=5, product=product)
        link = scm.Link(env=env, ID="L1", source=s1, sink=m1, cost=0, lead_time=lambda: 1)
        return s1, m1, link

    # ---- clock ------------------------------------------------------------

    def test_clock_counts_from_creation_and_restarts_on_reset(self):
        env = simpy.Environment()
        w1 = self._site(env)
        env.run(until=5)
        assert w1.stats.start_time == 0
        assert w1.stats.elapsed_time == 5
        w1.stats.reset()
        assert w1.stats.start_time == 5
        env.run(until=8)
        assert w1.stats.elapsed_time == 3

    # ---- disruptions ------------------------------------------------------

    def test_disruptions_counted_and_timed(self):
        # Disrupted at day 2 for 3 days (back at 5), then again at day 7.
        env = simpy.Environment()
        w1 = self._site(env, node_disrupt_time=lambda: 2, node_recovery_time=lambda: 3)
        env.run(until=6)
        assert w1.stats.disruptions == 1
        assert w1.stats.disrupted_time == 3
        env.run(until=8)   # disrupted again since day 7
        assert w1.stats.disruptions == 2
        assert w1.stats.disrupted_time == 4   # the ongoing day counts when read
        assert w1.stats.availability == 0.5
        assert w1.stats.get_statistics()["availability"] == 0.5

    def test_reset_during_a_disruption_counts_only_from_the_reset(self):
        env = simpy.Environment()
        w1 = self._site(env, node_disrupt_time=lambda: 2, node_recovery_time=lambda: 3)
        env.run(until=8)   # disrupted since day 7, back at day 10
        w1.stats.reset()
        assert w1.stats.disruptions == 0
        assert w1.stats.disrupted_time == 0
        env.run(until=11)
        assert w1.stats.disruptions == 0   # that disruption started before the reset
        assert w1.stats.disrupted_time == 2   # days 8 to 10
        assert w1.stats.availability == pytest.approx(1 - 2 / 3)

    def test_blocked_when_no_supplier_can_take_the_order(self):
        env = simpy.Environment()
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier")
        w1 = self._site(env)
        scm.Link(env=env, ID="L1", source=s1, sink=w1, cost=0, lead_time=lambda: 1)
        s1.node_status = "inactive"
        w1.place_order(20)
        env.run(until=1)
        assert w1.stats.blocked == [1, 20]
        assert w1.stats.demand_placed == [0, 0]

    def test_blocked_when_the_chosen_link_is_disrupted_when_the_order_starts(self):
        env = simpy.Environment()
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier")
        w1 = self._site(env)
        link = scm.Link(env=env, ID="L1", source=s1, sink=w1, cost=0, lead_time=lambda: 1)
        link.status = "inactive"
        env.process(w1.process_order(link, 20))
        env.run(until=1)
        assert w1.stats.blocked == [1, 20]
        assert w1.stats.demand_placed == [0, 0]

    def test_manufacturer_blocked_when_a_raw_material_has_no_supplier(self):
        env = simpy.Environment()
        s1, m1, link = self._factory(env)
        link.status = "inactive"
        env.process(m1.process_order(link, 10))
        env.run(until=1)
        assert m1.stats.blocked == [1, 10]
        assert m1.stats.demand_placed == [0, 0]

    # ---- inventory over time ----------------------------------------------

    def test_average_inventory_level_weights_each_level_by_its_time(self):
        # 10 units for 3 time units, then 4 units for 2: (30 + 8) / 5 = 7.6.
        env = simpy.Environment()
        w1 = self._site(env, initial_level=10)
        env.process(self._at(env, 3, lambda: w1.inventory.get(6)))
        env.run(until=5)
        assert w1.stats.inventory_level_time == 38   # includes days 3 to 5, with no event since
        assert w1.stats.avg_inventory_level == pytest.approx(7.6)

    def test_zero_inventory_time(self):
        env = simpy.Environment()
        w1 = self._site(env, initial_level=10)
        env.process(self._at(env, 2, lambda: w1.inventory.get(10)))
        env.run(until=6)
        assert w1.stats.zero_inventory_time == 4
        assert w1.stats.zero_inventory_share == pytest.approx(4 / 6)

    def test_inventory_values_after_a_reset_cover_only_the_time_since(self):
        # 10 units until day 5, 4 units after; reset at day 4, read at day 8:
        # (10 x 1 + 4 x 3) / 4 = 5.5.
        env = simpy.Environment()
        w1 = self._site(env, initial_level=10)
        env.process(self._at(env, 5, lambda: w1.inventory.get(6)))
        env.run(until=4)
        w1.stats.reset()
        env.run(until=8)
        assert w1.stats.inventory_level_time == 22
        assert w1.stats.avg_inventory_level == pytest.approx(5.5)
        assert w1.stats.zero_inventory_time == 0

    def test_inventory_values_are_none_without_a_finite_inventory(self):
        env = simpy.Environment()
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier")
        w1 = self._site(env, initial_level=10)
        dem = scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                         order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 1)
        env.run(until=3)
        for stats in (s1.stats, dem.stats):
            assert stats.inventory_level_time is None
            assert stats.avg_inventory_level is None
            assert stats.zero_inventory_time is None
            assert stats.zero_inventory_share is None

    # ---- orders that end badly ----------------------------------------------

    def test_lost_sales_customer_with_no_tolerance(self):
        # 3 units there, 10 wanted: the customer gets none and leaves.
        env = simpy.Environment()
        w1 = self._site(env, initial_level=3)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                   order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 10)
        env.run(until=1)
        assert w1.stats.lost_sales == [1, 10]
        assert w1.stats.shortage == [1, 7]

    def test_lost_sales_customer_takes_what_is_there(self):
        env = simpy.Environment()
        w1 = self._site(env, initial_level=3)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1, consume_available=True,
                   order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 10)
        env.run(until=1)
        assert w1.stats.lost_sales == [1, 7]

    def test_lost_sales_order_too_big_for_the_site(self):
        env = simpy.Environment()
        w1 = self._site(env, initial_level=0, capacity=5)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1, tolerance=10,
                   order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 10)
        env.run(until=1)
        assert w1.stats.lost_sales == [1, 10]

    def test_lost_sales_customer_gives_up_after_a_partial_delivery(self):
        # The customer wants 10, accepts parts of 2 or more, and waits 3 days.
        # 4 units arrive at day 1 and are passed on; 6 are never delivered.
        env = simpy.Environment()
        w1 = self._site(env, initial_level=0)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1, tolerance=3,
                   order_min_split_ratio=0.2,
                   order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 10)
        env.process(self._at(env, 1, lambda: w1.inventory.put(4)))
        env.run(until=5)
        assert w1.stats.lost_sales == [1, 6]

    def test_waiting_customer_served_in_full(self):
        # A customer waits for 10 units from day 0; they arrive at day 2.
        env = simpy.Environment()
        w1 = self._site(env, initial_level=0)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1, tolerance=100,
                   order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 10)
        env.process(self._at(env, 2, lambda: w1.inventory.put(10)))
        env.run(until=3)
        assert w1.stats.lost_sales == [0, 0]
        assert w1.stats.waited == [1, 10]
        assert w1.stats.waiting_time == 2
        assert w1.stats.demand_fulfilled == [1, 10]
        assert w1.stats.avg_waiting_time == 2

    def test_order_from_another_site_waits_at_its_supplier(self):
        # W1 orders 20 from W0, which has none until day 3; lead time 1.
        env = simpy.Environment()
        w0 = self._site(env, ID="W0", initial_level=0)
        w1 = self._site(env, ID="W1", initial_level=0)
        link = scm.Link(env=env, ID="L1", source=w0, sink=w1, cost=0, lead_time=lambda: 1)
        env.process(w1.process_order(link, 20))
        env.process(self._at(env, 3, lambda: w0.inventory.put(20)))
        env.run(until=5)
        assert w0.stats.waited == [1, 20]
        assert w0.stats.waiting_time == 3
        assert w0.stats.demand_fulfilled == [1, 20]
        assert w0.stats.avg_waiting_time == 3

    def test_raw_material_order_waits_at_its_supplier(self):
        # The supplier mines 10 a day from day 0; 30 ordered at day 0.5 are
        # there at day 2, so the order waits 1.5 days.
        env = simpy.Environment()
        s1, m1, link = self._factory(env)
        env.run(until=0.5)
        env.process(m1.process_order_raw("RM1", link, 30))
        env.run(until=5)
        assert s1.stats.waited == [1, 30]
        assert s1.stats.waiting_time == pytest.approx(1.5)

    def test_dropped_units_are_counted(self):
        # The case of TestReplenishmentDropAndDiscard scenario A: a delivery
        # arrives to a full inventory with no one waiting, and units are dropped.
        scm.set_seed(42)
        env = simpy.Environment()
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier")
        d1 = scm.InventoryNode(env=env, ID="D1", name="D1", node_type="distributor",
                               capacity=100, initial_level=100, inventory_holding_cost=0.1,
                               replenishment_policy=scm.SSReplenishment, policy_param={"s": 90, "S": 100},
                               product_buy_price=10, product_sell_price=12)
        scm.Link(env=env, ID="L1", source=s1, sink=d1, cost=1, lead_time=lambda: 5)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=d1, tolerance=2,
                   order_arrival_model=_scripted_seq([0, 0, 0, 1], tail=100),
                   order_quantity_model=_scripted_seq([1, 1, 60, 80], tail=1))
        with self.assertLogs("sim_trace", level="WARNING") as cm:
            env.run(until=10)
        dropped = sum(float(re.search(r"Dropped ([0-9.]+) units", m).group(1))
                      for m in cm.output if "Dropped" in m)
        assert dropped > 0
        assert d1.stats.dropped_qty == dropped

    def test_new_totals_are_zero_after_a_reset(self):
        env = simpy.Environment()
        w1 = self._site(env, initial_level=3, node_disrupt_time=lambda: 2, node_recovery_time=lambda: 1)
        scm.Demand(env=env, ID="dem", name="dem", demand_node=w1,
                   order_arrival_model=lambda: 1e6, order_quantity_model=lambda: 10)
        env.run(until=4)
        assert w1.stats.lost_sales == [1, 10]
        w1.stats.reset()
        for key in ("lost_sales", "blocked", "waited"):
            assert getattr(w1.stats, key) == [0, 0], key
        for key in ("disruptions", "disrupted_time", "waiting_time", "dropped_qty",
                    "inventory_level_time", "zero_inventory_time"):
            assert getattr(w1.stats, key) == 0, key

    # ---- network results --------------------------------------------------

    def test_network_adds_up_lost_sales(self):
        nodes = [{"ID": "S1", "name": "S1", "node_type": "infinite_supplier"}]
        for ID in ("R1", "R2"):
            nodes.append({"ID": ID, "name": ID, "node_type": "retailer", "capacity": 10, "initial_level": 3,
                          "inventory_holding_cost": 0, "replenishment_policy": None, "policy_param": {},
                          "product_buy_price": 1, "product_sell_price": 2})
        demands = [{"ID": f"c{ID}", "name": f"c{ID}", "demand_node": ID, "order_arrival_model": lambda: 1e6,
                    "order_quantity_model": lambda: 10} for ID in ("R1", "R2")]
        links = [{"ID": f"L{ID}", "source": "S1", "sink": ID, "cost": 0, "lead_time": lambda: 1}
                 for ID in ("R1", "R2")]
        net = scm.Network.build(nodes=nodes, links=links, demands=demands)
        net.as_dict()["nodes"]["R2"].node_status = "inactive"
        net.simulate(sim_time=1, logging=False)
        assert net.results["lost_sales"] == [1, 10]              # R1: no tolerance, 3 of 10 there
        assert net.results["disruption_lost_sales"] == [1, 10]   # R2 is disrupted


class TestBlockedMeansDisruptedSuppliers(unittest.TestCase):
    """``blocked`` counts replenishment orders that could not be placed because
    every supplier the site has (or the link to it) was disrupted. A site with
    no supplier at all is a mistake in how the network is built: it is warned
    about, and nothing is counted as blocked (§6.9)."""

    def test_site_with_no_supplier_is_warned_about_and_not_blocked(self):
        env = simpy.Environment()
        w1 = scm.InventoryNode(env=env, ID="W1", name="W1", node_type="retailer", capacity=100,
                               initial_level=0, inventory_holding_cost=0,
                               replenishment_policy=scm.SSReplenishment, policy_param={"s": 5, "S": 10},
                               product_buy_price=1, product_sell_price=2)
        with pytest.warns(UserWarning, match="has no supplier"):
            env.run(until=3)
        assert w1.stats.blocked == [0, 0]
        assert w1.stats.demand_placed == [0, 0]

    def _factory_missing_sugar(self, env):
        flour = scm.RawMaterial(ID="flour", name="flour", extraction_quantity=1, extraction_time=1,
                                mining_cost=0, cost=1)
        sugar = scm.RawMaterial(ID="sugar", name="sugar", extraction_quantity=1, extraction_time=1,
                                mining_cost=0, cost=1)
        product = scm.Product(ID="P", name="P", manufacturing_cost=1, manufacturing_time=1, sell_price=5,
                              buy_price=0, batch_size=10, raw_materials=[(flour, 1), (sugar, 1)])
        s_flour = scm.Supplier(env=env, ID="SF", name="SF", node_type="infinite_supplier", raw_material=flour)
        m1 = scm.Manufacturer(env=env, ID="M1", name="M1", capacity=100, initial_level=0,
                              inventory_holding_cost=0, replenishment_policy=None, policy_param=None,
                              product_sell_price=5, product=product)
        link = scm.Link(env=env, ID="LF", source=s_flour, sink=m1, cost=0, lead_time=lambda: 1)
        return m1, link

    def test_manufacturer_without_a_supplier_for_a_raw_material_is_not_blocked(self):
        # The product needs flour and sugar, but no supplier sells sugar.
        env = simpy.Environment()
        m1, link = self._factory_missing_sugar(env)
        with pytest.warns(UserWarning):
            env.run(until=1)
            m1.place_order(10)
            env.process(m1.process_order(link, 10))
            env.run(until=2)
        assert m1.stats.blocked == [0, 0]
        assert m1.stats.demand_placed == [0, 0]

    def test_has_suppliers(self):
        env = simpy.Environment()
        m1, link = self._factory_missing_sugar(env)
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="infinite_supplier")
        w1 = scm.InventoryNode(env=env, ID="W1", name="W1", node_type="retailer", capacity=100,
                               initial_level=0, inventory_holding_cost=0, replenishment_policy=None,
                               policy_param={}, product_buy_price=1, product_sell_price=2)
        assert not w1.has_suppliers()
        scm.Link(env=env, ID="L1", source=s1, sink=w1, cost=0, lead_time=lambda: 1)
        s1.node_status = "inactive"
        assert w1.has_suppliers()       # a disrupted supplier is still a supplier
        assert not m1.has_suppliers()   # no supplier sells sugar


class TestOrderLargerThanSupplierCapacityWarns(unittest.TestCase):
    """A supplier fills a replenishment order only when it holds the whole
    order, so an order larger than the supplier's capacity can never be filled
    (§3.27). Until other ways of filling an order are added, the user is warned.
    The order itself is placed as before."""

    def _warehouse(self, env, ID, capacity, initial_level):
        return scm.InventoryNode(env=env, ID=ID, name=ID, node_type="warehouse", capacity=capacity,
                                 initial_level=initial_level, inventory_holding_cost=0,
                                 replenishment_policy=None, policy_param={},
                                 product_buy_price=1, product_sell_price=2)

    def test_site_order_larger_than_supplier_capacity_warns(self):
        env = simpy.Environment()
        w0 = self._warehouse(env, "W0", capacity=100, initial_level=100)
        w1 = self._warehouse(env, "W1", capacity=float("inf"), initial_level=0)
        with pytest.warns(UserWarning, match="Supplier W0 can hold at most"):
            link = scm.Link(env=env, ID="L1", source=w0, sink=w1, cost=0, lead_time=lambda: 1)
        env.process(w1.process_order(link, 150))
        with pytest.warns(UserWarning, match="larger than its supplier's capacity"):
            env.run(until=1)
        assert w1.stats.demand_placed == [1, 150]   # placed as before
        assert w0.stats.backorder == [1, 150]       # and waiting

    def test_raw_material_order_larger_than_supplier_capacity_warns(self):
        env = simpy.Environment()
        rawmat = scm.RawMaterial(ID="RM1", name="RM1", extraction_quantity=10, extraction_time=1,
                                 mining_cost=0, cost=1)
        product = scm.Product(ID="P1", name="P1", manufacturing_cost=1, manufacturing_time=1,
                              raw_materials=[(rawmat, 1)], sell_price=5, buy_price=0, batch_size=100)
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="supplier", capacity=20,
                          initial_level=0, inventory_holding_cost=0, raw_material=rawmat)
        m1 = scm.Manufacturer(env=env, ID="M1", name="M1", capacity=100, initial_level=0,
                              inventory_holding_cost=0, replenishment_policy=None, policy_param=None,
                              product_sell_price=5, product=product)
        with pytest.warns(UserWarning, match="Supplier S1 can hold at most"):
            link = scm.Link(env=env, ID="L1", source=s1, sink=m1, cost=0, lead_time=lambda: 1)
        env.process(m1.process_order_raw("RM1", link, 30))
        with pytest.warns(UserWarning, match="larger than its supplier's capacity"):
            env.run(until=1)

    def test_order_that_fits_the_supplier_does_not_warn(self):
        import warnings
        env = simpy.Environment()
        w0 = self._warehouse(env, "W0", capacity=100, initial_level=0)
        w1 = self._warehouse(env, "W1", capacity=100, initial_level=0)
        link = scm.Link(env=env, ID="L1", source=w0, sink=w1, cost=0, lead_time=lambda: 1)
        env.process(w1.process_order(link, 100))
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            env.run(until=1)


class TestLinkWarnsWhenBuyerCanOrderMoreThanSupplierHolds(unittest.TestCase):
    """When a link is created, the user is warned if its buyer can order more
    than its supplier can ever hold: such an order would never be filled, and
    the buyer would wait for it for ever (§3.27)."""

    def _warehouse(self, env, ID, capacity):
        return scm.InventoryNode(env=env, ID=ID, name=ID, node_type="warehouse", capacity=capacity,
                                 initial_level=0, inventory_holding_cost=0, replenishment_policy=None,
                                 policy_param={}, product_buy_price=1, product_sell_price=2)

    def _factory(self, env, supplier_capacity, factory_capacity, quantity_per_unit):
        rawmat = scm.RawMaterial(ID="RM1", name="RM1", extraction_quantity=10, extraction_time=1,
                                 mining_cost=0, cost=1)
        product = scm.Product(ID="P1", name="P1", manufacturing_cost=1, manufacturing_time=1,
                              raw_materials=[(rawmat, quantity_per_unit)], sell_price=5, buy_price=0,
                              batch_size=100)
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="supplier", capacity=supplier_capacity,
                          initial_level=0, inventory_holding_cost=0, raw_material=rawmat)
        m1 = scm.Manufacturer(env=env, ID="M1", name="M1", capacity=factory_capacity, initial_level=0,
                              inventory_holding_cost=0, replenishment_policy=None, policy_param=None,
                              product_sell_price=5, product=product)
        return s1, m1

    def test_buyer_with_a_larger_capacity_is_warned_about(self):
        env = simpy.Environment()
        d1 = self._warehouse(env, "D1", capacity=100)
        r1 = self._warehouse(env, "R1", capacity=200)
        with pytest.warns(UserWarning, match=r"D1 .* R1 .* for ever"):
            scm.Link(env=env, ID="L1", source=d1, sink=r1, cost=0, lead_time=lambda: 1)

    def test_buyer_with_no_capacity_limit_is_warned_about(self):
        env = simpy.Environment()
        d1 = self._warehouse(env, "D1", capacity=100)
        r1 = self._warehouse(env, "R1", capacity=float("inf"))
        with pytest.warns(UserWarning, match="R1"):
            scm.Link(env=env, ID="L1", source=d1, sink=r1, cost=0, lead_time=lambda: 1)

    def test_manufacturer_counts_raw_material_per_product_unit(self):
        # 150 product units at 2 units of raw material each: up to 300 units
        # of raw material, more than the supplier's 200.
        env = simpy.Environment()
        s1, m1 = self._factory(env, supplier_capacity=200, factory_capacity=150, quantity_per_unit=2)
        with pytest.warns(UserWarning, match="M1"):
            scm.Link(env=env, ID="L1", source=s1, sink=m1, cost=0, lead_time=lambda: 1)

    def test_no_warning_when_the_supplier_can_hold_what_the_buyer_orders(self):
        import warnings
        env = simpy.Environment()
        d1 = self._warehouse(env, "D1", capacity=200)
        r1 = self._warehouse(env, "R1", capacity=200)
        s1, m1 = self._factory(env, supplier_capacity=200, factory_capacity=150, quantity_per_unit=1)
        infinite = scm.Supplier(env=env, ID="S0", name="S0", node_type="infinite_supplier")
        r2 = self._warehouse(env, "R2", capacity=float("inf"))
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            scm.Link(env=env, ID="L1", source=d1, sink=r1, cost=0, lead_time=lambda: 1)
            scm.Link(env=env, ID="L2", source=s1, sink=m1, cost=0, lead_time=lambda: 1)
            scm.Link(env=env, ID="L3", source=infinite, sink=r2, cost=0, lead_time=lambda: 1)


class TestLinkStatistics(unittest.TestCase):
    """Each link records the replenishment orders its buyer placed over it,
    what arrived, how long the orders waited and travelled, what they cost,
    and the link's own disruptions (§6.8). Small networks with fixed times, so
    every number can be worked out by hand."""

    def _site(self, env, ID, initial_level=0, capacity=float("inf"), **kwargs):
        # A site with no replenishment policy: orders are placed by the test.
        return scm.InventoryNode(
            env=env, ID=ID, name=ID, node_type="warehouse",
            capacity=capacity, initial_level=initial_level,
            inventory_holding_cost=0, replenishment_policy=None, policy_param={},
            product_buy_price=1, product_sell_price=2, **kwargs,
        )

    def _at(self, env, day, action):
        yield env.timeout(day)
        action()

    def _pair(self, env, supplier_level, cost=3, lead_time=2):
        # W1 buys from W0 over L1. W0 has no capacity limit, so the link
        # warning about buyers ordering more than the supplier holds stays quiet.
        w0 = self._site(env, "W0", initial_level=supplier_level)
        w1 = self._site(env, "W1")
        link = scm.Link(env=env, ID="L1", source=w0, sink=w1, cost=cost, lead_time=lambda: lead_time)
        return w0, w1, link

    # ---- orders ---------------------------------------------------------------

    def test_order_served_at_once(self):
        env = simpy.Environment()
        w0, w1, link = self._pair(env, supplier_level=50)
        env.process(w1.process_order(link, 20))
        env.run(until=3)
        s = link.stats
        assert s.demand_placed == [1, 20]
        assert s.fulfillment_received == [1, 20]
        assert s.shortage == [0, 0]
        assert s.backorder == [0, 0]
        assert s.waited == [0, 0]
        assert s.transportation_cost == 3
        assert s.inventory_spend_cost == 20   # 20 units at W1's buy price of 1
        assert s.waiting_time == 0
        assert s.lead_time == 2
        assert s.avg_waiting_time == 0
        assert s.avg_lead_time == 2
        assert s.avg_order_cycle_time == 2
        assert s.fill_rate == 1
        assert s.order_fill_rate == 1

    def test_order_that_waits_at_the_supplier(self):
        # W0 has nothing until day 3. The order waits 3 days, then travels 1.
        env = simpy.Environment()
        w0, w1, link = self._pair(env, supplier_level=0, lead_time=1)
        env.process(w1.process_order(link, 20))
        env.process(self._at(env, 3, lambda: w0.inventory.put(20)))
        env.run(until=2)
        s = link.stats
        assert s.backorder == [1, 20]
        assert s.waited == [1, 20]
        assert s.shortage == [1, 20]
        assert s.fulfillment_received == [0, 0]
        assert s.avg_waiting_time is None   # nothing has arrived yet
        env.run(until=5)
        assert s.backorder == [0, 0]
        assert s.waited == [1, 20]          # a running total, unlike backorder
        assert s.waiting_time == 3
        assert s.lead_time == 1
        assert s.avg_order_cycle_time == 4
        assert s.fill_rate == 0
        assert s.order_fill_rate == 0

    def test_fill_rate_counts_units_and_orders(self):
        # W0 holds 25. An order of 20 is sent at once; the next one, of 10,
        # finds only 5 and waits until 5 more arrive at day 2. By units 20 of
        # 30 were sent at once, by orders 1 of 2.
        env = simpy.Environment()
        w0, w1, link = self._pair(env, supplier_level=25, lead_time=1)
        env.process(w1.process_order(link, 20))
        env.process(w1.process_order(link, 10))
        env.process(self._at(env, 2, lambda: w0.inventory.put(5)))
        env.run(until=4)
        s = link.stats
        assert s.demand_placed == [2, 30]
        assert s.waited == [1, 10]
        assert s.shortage == [1, 5]
        assert s.fill_rate == pytest.approx(2 / 3)
        assert s.order_fill_rate == pytest.approx(0.5)
        assert s.waiting_time == 2
        assert s.avg_waiting_time == 1   # 2 days over 2 orders received

    def test_raw_material_order(self):
        # The supplier mines 10 a day; 30 ordered at day 0.5 are there at day
        # 2, so the order waits 1.5 days, then travels 1 day.
        env = simpy.Environment()
        rawmat = scm.RawMaterial(ID="RM1", name="RM1", extraction_quantity=10, extraction_time=1,
                                 mining_cost=0, cost=2)
        product = scm.Product(ID="P1", name="P1", manufacturing_cost=1, manufacturing_time=1,
                              raw_materials=[(rawmat, 1)], sell_price=5, buy_price=0, batch_size=100)
        s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="supplier", capacity=100,
                          initial_level=0, inventory_holding_cost=0, raw_material=rawmat)
        m1 = scm.Manufacturer(env=env, ID="M1", name="M1", capacity=100, initial_level=0,
                              inventory_holding_cost=0, replenishment_policy=None, policy_param=None,
                              product_sell_price=5, product=product)
        link = scm.Link(env=env, ID="L1", source=s1, sink=m1, cost=4, lead_time=lambda: 1)
        env.run(until=0.5)
        env.process(m1.process_order_raw("RM1", link, 30))
        env.run(until=5)
        s = link.stats
        assert s.demand_placed == [1, 30]
        assert s.fulfillment_received == [1, 30]
        assert s.waited == [1, 30]
        assert s.shortage == s1.stats.shortage
        assert s.waiting_time == pytest.approx(1.5)
        assert s.lead_time == 1
        assert s.transportation_cost == 4
        assert s.inventory_spend_cost == 60   # 30 units at the supplier's sell price of 2

    def test_blocked_when_the_link_is_disrupted_as_the_order_starts(self):
        env = simpy.Environment()
        w0, w1, link = self._pair(env, supplier_level=50)
        link.status = "inactive"
        env.process(w1.process_order(link, 20))
        env.run(until=1)
        assert link.stats.blocked == [1, 20]
        assert link.stats.demand_placed == [0, 0]
        assert link.stats.backorder == [0, 0]
        assert w1.stats.blocked == [1, 20]

    def test_order_blocked_before_a_link_is_chosen_is_not_on_any_link(self):
        env = simpy.Environment()
        w0, w1, link = self._pair(env, supplier_level=50)
        w0.node_status = "inactive"
        w1.place_order(20)
        env.run(until=1)
        assert w1.stats.blocked == [1, 20]
        assert link.stats.blocked == [0, 0]

    # ---- disruptions ------------------------------------------------------------

    def _disrupted_link(self, env):
        # Disrupted at day 2 for 3 days (back at 5), then again at day 7.
        s0 = scm.Supplier(env=env, ID="S0", name="S0", node_type="infinite_supplier")
        w1 = self._site(env, "W1")
        return scm.Link(env=env, ID="L1", source=s0, sink=w1, cost=0, lead_time=lambda: 1,
                        link_disrupt_time=lambda: 2, link_recovery_time=lambda: 3)

    def test_disruptions_counted_and_timed(self):
        env = simpy.Environment()
        link = self._disrupted_link(env)
        env.run(until=6)
        assert link.stats.disruptions == 1
        assert link.stats.disrupted_time == 3
        env.run(until=8)
        assert link.stats.disruptions == 2
        assert link.stats.disrupted_time == 4   # the ongoing day counts when read
        assert link.stats.availability == 0.5

    def test_reset_during_a_disruption_counts_only_from_the_reset(self):
        env = simpy.Environment()
        link = self._disrupted_link(env)
        env.run(until=8)   # disrupted since day 7, back at day 10
        link.stats.reset()
        assert link.stats.disruptions == 0
        assert link.stats.disrupted_time == 0
        env.run(until=11)
        assert link.stats.disruptions == 0   # that disruption started before the reset
        assert link.stats.disrupted_time == 2   # days 8 to 10
        assert link.stats.availability == pytest.approx(1 - 2 / 3)

    # ---- per time unit and spreads ---------------------------------------------

    def _orders_at(self, env, link, times, quantity):
        for t in times:
            yield env.timeout(t - env.now)
            env.process(link.sink.process_order(link, quantity))

    def _bursty_link(self, env):
        # 60 units at day 3 and 60 at day 7, nothing in between (the example
        # in the LinkStatistics docstring).
        s0 = scm.Supplier(env=env, ID="S0", name="S0", node_type="infinite_supplier")
        w1 = self._site(env, "W1")
        link = scm.Link(env=env, ID="L1", source=s0, sink=w1, cost=0, lead_time=lambda: 1)
        env.process(self._orders_at(env, link, [3, 7], 60))
        return link

    def test_orders_per_time_unit_and_the_two_spreads(self):
        import statistics
        env = simpy.Environment()
        link = self._bursty_link(env)
        env.run(until=10)
        s = link.stats
        assert s.orders_per_time_unit == pytest.approx(0.2)
        assert s.units_per_time_unit == pytest.approx(12)
        assert s.order_size_mean == 60
        assert s.order_size_std == 0   # every order is the same size
        per_time_unit = [0, 0, 0, 60, 0, 0, 0, 60, 0, 0]
        assert s.units_per_time_unit_std == pytest.approx(statistics.stdev(per_time_unit))

    def test_reading_the_spread_changes_nothing(self):
        env_a, env_b = simpy.Environment(), simpy.Environment()
        link_a, link_b = self._bursty_link(env_a), self._bursty_link(env_b)
        for t in (0.5, 3.5, 5, 7.25):   # read link_a now and then, never link_b
            env_a.run(until=t)
            link_a.stats.units_per_time_unit_std
        env_a.run(until=10)
        env_b.run(until=10)
        assert link_a.stats.units_per_time_unit_std == link_b.stats.units_per_time_unit_std

    def test_spreads_are_none_with_fewer_than_two_values(self):
        env = simpy.Environment()
        link = self._bursty_link(env)
        env.run(until=0.5)
        assert link.stats.units_per_time_unit_std is None   # no time unit has finished
        assert link.stats.order_size_mean is None
        env.run(until=4)
        assert link.stats.order_size_mean == 60
        assert link.stats.order_size_std is None   # one order so far

    def test_values_with_nothing_to_divide_by_are_none(self):
        env = simpy.Environment()
        w0, w1, link = self._pair(env, supplier_level=50)
        s = link.stats
        assert s.elapsed_time == 0
        for key in ("availability", "orders_per_time_unit", "units_per_time_unit", "avg_waiting_time",
                    "avg_lead_time", "avg_order_cycle_time", "fill_rate", "order_fill_rate",
                    "order_size_mean", "order_size_std", "units_per_time_unit_std"):
            assert getattr(s, key) is None, key
        env.run(until=5)
        assert s.orders_per_time_unit == 0
        assert s.availability == 1

    # ---- reset ------------------------------------------------------------------

    def test_reset_keeps_waiting_orders_and_restarts_the_counting(self):
        # The order waits at W0 from day 0; W0 gets the units at day 3 and the
        # order arrives at day 4. Reset at day 2, while it waits.
        env = simpy.Environment()
        w0, w1, link = self._pair(env, supplier_level=0, lead_time=1)
        env.process(w1.process_order(link, 20))
        env.process(self._at(env, 3, lambda: w0.inventory.put(20)))
        env.run(until=2)
        link.stats.reset()
        s = link.stats
        assert s.start_time == 2
        assert s.backorder == [1, 20]   # still waiting
        for key in ("demand_placed", "waited", "shortage", "blocked", "fulfillment_received"):
            assert getattr(s, key) == [0, 0], key
        for key in ("transportation_cost", "inventory_spend_cost", "waiting_time", "lead_time", "disruptions"):
            assert getattr(s, key) == 0, key
        assert s.order_size_mean is None
        env.run(until=5)
        assert s.backorder == [0, 0]   # back to zero, not below
        assert s.fulfillment_received == [1, 20]   # received after the reset
        assert s.demand_placed == [0, 0]           # placed before it
        assert s.waiting_time == 3
        assert s.elapsed_time == 3

    def test_waiting_time_is_added_on_arrival_with_the_order(self):
        # Served at day 3 after waiting 3 days, arrives at day 4. A reset at
        # day 3.5 falls in between: the order counts as received after the
        # reset, so its waiting time must count after it too, or the average
        # would divide 0 days by 1 order.
        env = simpy.Environment()
        w0, w1, link = self._pair(env, supplier_level=0, lead_time=1)
        env.process(w1.process_order(link, 20))
        env.process(self._at(env, 3, lambda: w0.inventory.put(20)))
        env.run(until=3.5)
        link.stats.reset()
        env.run(until=5)
        assert link.stats.fulfillment_received == [1, 20]
        assert link.stats.avg_waiting_time == 3
        assert link.stats.avg_lead_time == 1

    # ---- reading ----------------------------------------------------------------

    def test_get_statistics_has_every_key(self):
        env = simpy.Environment()
        w0, w1, link = self._pair(env, supplier_level=50)
        stats = link.stats.get_statistics()
        assert list(stats) == scm.LinkStatistics._stats_keys
        assert stats["name"] == "L1 statistics"

    def test_link_get_statistics_still_gives_only_the_status(self):
        env = simpy.Environment()
        w0, w1, link = self._pair(env, supplier_level=50)
        assert link.get_statistics() == {"status": "active"}

    def test_update_stats_warns_about_an_unknown_name(self):
        env = simpy.Environment()
        w0, w1, link = self._pair(env, supplier_level=50)
        with pytest.warns(UserWarning, match="unknown statistic 'demand_placd'"):
            link.stats.update_stats(demand_placd=[1, 5])
        with pytest.warns(UserWarning, match="unknown statistic 'fill_rate'"):
            link.stats.update_stats(fill_rate=1)   # worked out when read, not a total
        link.stats.update_stats(demand_placed=[1, 5], lead_time=2)
        assert link.stats.demand_placed == [1, 5]
        assert link.stats.lead_time == 2


class TestLinkStatisticsAddUpToNodes(unittest.TestCase):
    """The link statistics repeat, per link, what the node statistics record,
    so the totals over a site's links equal the site's own figures (§6.8)."""

    def _total(self, links, key):
        values = [getattr(link.stats, key) for link in links]
        if isinstance(values[0], list):
            return [sum(v[0] for v in values), sum(v[1] for v in values)]
        return sum(values)

    def _assert_close(self, a, b, what):
        assert a == pytest.approx(b), what

    def _check(self, sc):
        customer_sites = {d.demand_node.ID for d in sc["demands"].values()}
        for node in sc["nodes"].values():
            if node.suppliers:
                # What the buyer ordered and received, over all its supplier links.
                for key in ("demand_placed", "fulfillment_received", "transportation_cost", "inventory_spend_cost"):
                    self._assert_close(getattr(node.stats, key), self._total(node.suppliers, key), (node.ID, key))
            if node.buyers and node.ID not in customer_sites:
                # What the supplier received from its buyers, over all its buyer links.
                for node_key, link_key in (("demand_received", "demand_placed"), ("shortage", "shortage"),
                                           ("backorder", "backorder"), ("waited", "waited")):
                    self._assert_close(getattr(node.stats, node_key), self._total(node.buyers, link_key),
                                       (node.ID, node_key))

    def test_buyer_with_two_suppliers(self):
        for seed in range(3):
            scm.set_seed(seed)
            r = random.Random(seed)
            site = {"node_type": "distributor", "inventory_holding_cost": 0.1,
                    "replenishment_policy": scm.SSReplenishment, "product_buy_price": 10, "product_sell_price": 12}
            sc = scm.create_sc_net(
                nodes=[{"ID": "S1", "name": "S1", "node_type": "infinite_supplier"},
                       {"ID": "S2", "name": "S2", "node_type": "infinite_supplier"},
                       dict(site, ID="D1", name="D1", capacity=200, initial_level=80,
                            policy_param={"s": 60, "S": 200}, failure_p=0.03, node_recovery_time=lambda: 2),
                       dict(site, ID="R1", name="R1", node_type="retailer", capacity=60, initial_level=30,
                            policy_param={"s": 20, "S": 60}),
                       dict(site, ID="R2", name="R2", node_type="retailer", capacity=60, initial_level=30,
                            policy_param={"s": 25, "S": 60})],
                links=[{"ID": "L1", "source": "S1", "sink": "D1", "cost": 5, "lead_time": lambda: 2,
                        "link_disrupt_time": lambda: 10, "link_recovery_time": lambda: 5},
                       {"ID": "L2", "source": "S2", "sink": "D1", "cost": 7, "lead_time": lambda: 1},
                       {"ID": "L3", "source": "D1", "sink": "R1", "cost": 2, "lead_time": lambda: r.choice([1, 2])},
                       {"ID": "L4", "source": "D1", "sink": "R2", "cost": 2, "lead_time": lambda: 1}],
                demands=[{"ID": "c1", "name": "c1", "demand_node": "R1", "tolerance": 3,
                          "order_arrival_model": lambda: r.expovariate(1.5),
                          "order_quantity_model": lambda: r.randint(1, 12)},
                         {"ID": "c2", "name": "c2", "demand_node": "R2", "consume_available": True,
                          "order_arrival_model": lambda: 1, "order_quantity_model": lambda: r.randint(5, 15)}])
            scm.simulate_sc_net(sc, sim_time=150, logging=False)
            links = sc["links"]
            # Both suppliers of D1 got orders: L1 is disrupted every 10 days.
            assert links["L1"].stats.demand_placed[0] > 0 and links["L2"].stats.demand_placed[0] > 0
            assert links["L1"].stats.disruptions > 0
            assert links["L3"].stats.waited[0] + links["L4"].stats.waited[0] > 0   # some orders waited at D1
            self._check(sc)

    def test_manufacturer_with_two_raw_materials(self):
        for seed in range(3):
            scm.set_seed(seed)
            r = random.Random(seed)
            env = simpy.Environment()
            rm1 = scm.RawMaterial(ID="RM1", name="RM1", extraction_quantity=15, extraction_time=1,
                                  mining_cost=0.1, cost=1)
            rm2 = scm.RawMaterial(ID="RM2", name="RM2", extraction_quantity=40, extraction_time=2,
                                  mining_cost=0.05, cost=0.5)
            product = scm.Product(ID="P1", name="P1", manufacturing_cost=2, manufacturing_time=1, sell_price=12,
                                  buy_price=0, batch_size=25, raw_materials=[(rm1, 2), (rm2, 3)])
            s1 = scm.Supplier(env=env, ID="S1", name="S1", node_type="supplier", capacity=400, initial_level=60,
                              inventory_holding_cost=0.01, raw_material=rm1,
                              node_disrupt_time=lambda: r.randint(8, 15), node_recovery_time=lambda: 3)
            s2 = scm.Supplier(env=env, ID="S2", name="S2", node_type="supplier", capacity=400, initial_level=20,
                              inventory_holding_cost=0.01, raw_material=rm1)
            s3 = scm.Supplier(env=env, ID="S3", name="S3", node_type="supplier", capacity=600, initial_level=100,
                              inventory_holding_cost=0.01, raw_material=rm2)
            m1 = scm.Manufacturer(env=env, ID="M1", name="M1", capacity=150, initial_level=30,
                                  inventory_holding_cost=0.1, replenishment_policy=scm.SSReplenishment,
                                  policy_param={"s": 40, "S": 120}, product_sell_price=12, product=product)
            w1 = scm.InventoryNode(env=env, ID="W1", name="W1", node_type="warehouse", capacity=80, initial_level=40,
                                   inventory_holding_cost=0.2, replenishment_policy=scm.SSReplenishment,
                                   policy_param={"s": 30, "S": 80}, product_buy_price=12, product_sell_price=16)
            links = [scm.Link(env=env, ID="L1", source=s1, sink=m1, cost=3, lead_time=lambda: 1),
                     scm.Link(env=env, ID="L2", source=s2, sink=m1, cost=4, lead_time=lambda: r.choice([1, 2])),
                     scm.Link(env=env, ID="L3", source=s3, sink=m1, cost=2, lead_time=lambda: 2),
                     scm.Link(env=env, ID="L4", source=m1, sink=w1, cost=4, lead_time=lambda: 2)]
            demand = scm.Demand(env=env, ID="d1", name="d1", demand_node=w1, tolerance=2,
                                order_arrival_model=lambda: 1, order_quantity_model=lambda: r.randint(5, 20))
            sc = scm.create_sc_net(env=env, nodes=[s1, s2, s3, m1, w1], links=links, demands=[demand])
            scm.simulate_sc_net(sc, sim_time=150, logging=False)
            # Raw material RM1 came from both of its suppliers (S1 is disrupted now and then).
            assert sc["links"]["L1"].stats.demand_placed[0] > 0 and sc["links"]["L2"].stats.demand_placed[0] > 0
            assert sum(l.stats.waited[0] for l in links[:3]) > 0   # some raw-material orders waited
            self._check(sc)
