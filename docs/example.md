# SupplyNetPy Examples

## A simple three node supply chain

Let's create a supply chain network for a single product inventory with three nodes, a supplier, a manufacturer, and a retailer. The retailer has the option to replenish its inventory by obtaining products directly from the manufacturer. Meanwhile, the manufacturer can restock its own inventory by sourcing materials from the supplier to produce the goods.

~~~
# let us import the library
import SupplyNetPy.Components as scm

# First off, let us set up a SimPy environment where we can play around with
# and simulate how the supply chain network operates.
import simpy
env = simpy.Environment()
~~~

Before creating supply chain nodes, which include retailers, manufacturers, and suppliers, it is imperative to create a product. This product will serve as the fundamental element that flows through each node of the supply chain, linking all stakeholders in a cohesive and operational network.

The product is defined using SupplyNetPy's `Product` class, which includes essential details such as _sku_, _name_, _description_, _product type_, and _shelf life_, ensuring a comprehensive and efficient inventory management approach.

~~~
product1 = scm.Product(sku="12325",name="TShirt",description="Cloths",
                       cost=800,profit=100,product_type="Non-perishable",shelf_life=None)
~~~

[sS]: ## "Reorder level-based inventory replenishment policy: In this approach, inventory levels are continuously monitored. When inventory levels drop below a certain threshold 's', an order is placed to restock it to its full capacity 'S'."

Let's now create retailer, manufacturer, and supplier nodes in the supply chain network. These nodes will be created using SupplyNetPy's `Retailer`, `Manufacturer`, and `Supplier` classes. They will require basic information such as ID, name, node type, location, and inventory details including capacity, reorder point, inventory products, and hold cost. If the inventory type and replenishment policy are not specified, the default values will be _single product inventory_ and [(s,S) replenishment policy][sS].

~~~
supplier1 = scm.Supplier(env=env,name="supplier1",node_id=123,location="Goa",
                         inv_capacity=800,inv_holding_cost=1,reorder_level=600)

manufacturer1 = scm.Manufacturer(env=env,name="man1",node_id=124,location="Mumbai",
                                 production_cost=100,production_level=200,products=[product1],
                                 inv_capacity=600,inv_holding_cost=2,reorder_level=300)

retailer1 = scm.Retailer(env=env,name=f"retailer1",node_id=125,location="Mumbai",
                         products=[product1],inv_capacity=300,
                         inv_holding_cost=3,reorder_level=100)
~~~

To stimulate product movement within our network, we need to generate demand. Traditionally, retailers are the main points of contact for real customer demand. However, we can also create demand directly at the manufacturer node. Imagine a scenario in which a manufacturer not only supplies products to retailers but also directly responds to customer orders for personalized items. For example, consider the manufacturing of custom-designed T-shirts for a university baseball team. We use the `Demand` class from SupplyNetPy to accomplish this. The `Demand` class can currently model demand as a standard distribution. So, we need to specify the name of the distribution and distribution parameters. It will model the arrival of the customers. The `demand_dist` parameter specifies the distribution of the purchases (quantity of units in an order).

~~~
demand_ret1 = scm.Demand(env=env, arr_dist="Poisson",arr_params=[6],node=retailer1,
                         demand_dist="Uniform",demand_params=[1,10])
demand_man1 = scm.Demand(env=env, arr_dist="Poisson",arr_params=[1],node=manufacturer1,
                         demand_dist="Uniform",demand_params=[1,3])
~~~

Now that we have created all the essential components in the supply chain, we need to connect them in a network. SupplyNetPy uses the `Link` class to connect any two supply chain nodes. We have to specify the "to" and "from" nodes, along with additional essential parameters like lead time, transport cost, and distance.

~~~
link1 = scm.Link(from_node=supplier1,to_node=manufacturer1,
                 lead_time=3,transportation_cost=100,link_distance=300)

link2 = scm.Link(from_node=manufacturer1,to_node=retailer1,
                 lead_time=2,transportation_cost=70,link_distance=200)
~~~

Let us leverage SupplyNetPy's create_sc and simulate_sc_net functions to assemble the supply chain components we created above in a single network and simulate it. 

~~~
scnet = scm.create_sc(products=[product1],
                      nodes = [supplier1,manufacturer1,retailer1],
                      links = [link1, link2],
                      demands = [demand_ret1,demand_man1])

scm.simulate_sc_net(env,scnet,sim_time=10)
~~~

### Code output

Below is the simulation log printed on the console by running the above code snippet.
<div style="overflow-y: auto; padding: 0px; max-height: 500px;">
```bash
INFO 2024-07-24 17:43:16,726 sim_trace - : A link from 'supplier1' to 'man1' is created.
INFO 2024-07-24 17:43:16,727 sim_trace - : A link from 'man1' to 'retailer1' is created.
INFO 2024-07-24 17:43:16,727 sim_trace - Number of nodes in the network: 3
INFO 2024-07-24 17:43:16,727 sim_trace - Number of edges in the network: 2
INFO 2024-07-24 17:43:16,727 sim_trace -         Number of suppliers: 1
INFO 2024-07-24 17:43:16,727 sim_trace -         Number of manufacturers: 1
INFO 2024-07-24 17:43:16,727 sim_trace -         Number of distributors: 0
INFO 2024-07-24 17:43:16,727 sim_trace -         Number of retailers: 1
INFO 2024-07-24 17:43:16,727 sim_trace - Name: supplier1
INFO 2024-07-24 17:43:16,727 sim_trace - ID: 123
INFO 2024-07-24 17:43:16,727 sim_trace - Type: Supplier
INFO 2024-07-24 17:43:16,733 sim_trace - Location: Goa
INFO 2024-07-24 17:43:16,733 sim_trace - Reliability: 1
INFO 2024-07-24 17:43:16,733 sim_trace - Resilience: 1
INFO 2024-07-24 17:43:16,734 sim_trace - Criticality: 1
INFO 2024-07-24 17:43:16,734 sim_trace - Inventory capacity: 800
INFO 2024-07-24 17:43:16,734 sim_trace - Inventory holding cost: 1
INFO 2024-07-24 17:43:16,735 sim_trace - Inventory reorder level: 0
INFO 2024-07-24 17:43:16,735 sim_trace - Inventory reorder period: 1
INFO 2024-07-24 17:43:16,736 sim_trace - Inventory type: Single
INFO 2024-07-24 17:43:16,736 sim_trace - Inventory replenishment policy: sS
INFO 2024-07-24 17:43:16,736 sim_trace - Name: man1
INFO 2024-07-24 17:43:16,737 sim_trace - ID: 124
INFO 2024-07-24 17:43:16,737 sim_trace - Type: Manufacturer
INFO 2024-07-24 17:43:16,739 sim_trace - Location: Mumbai
INFO 2024-07-24 17:43:16,739 sim_trace - Reliability: 1
INFO 2024-07-24 17:43:16,739 sim_trace - Resilience: 1
INFO 2024-07-24 17:43:16,739 sim_trace - Criticality: 1
INFO 2024-07-24 17:43:16,739 sim_trace - Inventory capacity: 600
INFO 2024-07-24 17:43:16,739 sim_trace - Inventory holding cost: 2
INFO 2024-07-24 17:43:16,742 sim_trace - Inventory reorder level: 300
INFO 2024-07-24 17:43:16,742 sim_trace - Inventory reorder period: 1
INFO 2024-07-24 17:43:16,743 sim_trace - Inventory type: Single
INFO 2024-07-24 17:43:16,743 sim_trace - Inventory replenishment policy: sS
INFO 2024-07-24 17:43:16,744 sim_trace - Name: retailer1
INFO 2024-07-24 17:43:16,744 sim_trace - ID: 125
INFO 2024-07-24 17:43:16,744 sim_trace - Type: retailer
INFO 2024-07-24 17:43:16,746 sim_trace - Location: Mumbai
INFO 2024-07-24 17:43:16,746 sim_trace - Reliability: 1
INFO 2024-07-24 17:43:16,747 sim_trace - Resilience: 1
INFO 2024-07-24 17:43:16,748 sim_trace - Criticality: 1
INFO 2024-07-24 17:43:16,748 sim_trace - Inventory capacity: 300
INFO 2024-07-24 17:43:16,749 sim_trace - Inventory holding cost: 3
INFO 2024-07-24 17:43:16,750 sim_trace - Inventory reorder level: 100
INFO 2024-07-24 17:43:16,752 sim_trace - Inventory reorder period: 1
INFO 2024-07-24 17:43:16,752 sim_trace - Inventory type: Single
INFO 2024-07-24 17:43:16,754 sim_trace - Inventory replenishment policy: sS
INFO 2024-07-24 17:43:16,755 sim_trace - Link from: supplier1
INFO 2024-07-24 17:43:16,755 sim_trace - to: man1
INFO 2024-07-24 17:43:16,756 sim_trace - Lead time: 3
INFO 2024-07-24 17:43:16,756 sim_trace - Tranportation cost: 100
INFO 2024-07-24 17:43:16,757 sim_trace - Distance: 300 Km
INFO 2024-07-24 17:43:16,758 sim_trace - Transport type: road
INFO 2024-07-24 17:43:16,759 sim_trace - Load capacity: 0
INFO 2024-07-24 17:43:16,760 sim_trace - Min shipment quantity: 0
INFO 2024-07-24 17:43:16,760 sim_trace - Link failuer probability: 0
INFO 2024-07-24 17:43:16,761 sim_trace - CO2 cost: 0
INFO 2024-07-24 17:43:16,761 sim_trace - Reliability: 1
INFO 2024-07-24 17:43:16,762 sim_trace - Resilience: 1
INFO 2024-07-24 17:43:16,762 sim_trace - Criticality: 0
INFO 2024-07-24 17:43:16,763 sim_trace - Link from: man1
INFO 2024-07-24 17:43:16,763 sim_trace - to: retailer1
INFO 2024-07-24 17:43:16,764 sim_trace - Lead time: 2
INFO 2024-07-24 17:43:16,764 sim_trace - Tranportation cost: 70
INFO 2024-07-24 17:43:16,764 sim_trace - Distance: 200 Km
INFO 2024-07-24 17:43:16,765 sim_trace - Transport type: road
INFO 2024-07-24 17:43:16,766 sim_trace - Load capacity: 0
INFO 2024-07-24 17:43:16,767 sim_trace - Min shipment quantity: 0
INFO 2024-07-24 17:43:16,768 sim_trace - Link failuer probability: 0
INFO 2024-07-24 17:43:16,768 sim_trace - CO2 cost: 0
INFO 2024-07-24 17:43:16,769 sim_trace - Reliability: 1
INFO 2024-07-24 17:43:16,769 sim_trace - Resilience: 1
INFO 2024-07-24 17:43:16,770 sim_trace - Criticality: 0
INFO 2024-07-24 17:43:16,771 sim_trace - This demand is generated for node retailer1.
INFO 2024-07-24 17:43:16,771 sim_trace - Customer arrival is modeled by Poisson distribution.
INFO 2024-07-24 17:43:16,772 sim_trace - The distribution parameters are [6].
INFO 2024-07-24 17:43:16,772 sim_trace - Per customer demand is modeled using Uniform distribution.
INFO 2024-07-24 17:43:16,772 sim_trace - parameters are: [1, 10]
INFO 2024-07-24 17:43:16,774 sim_trace - This demand is generated for node man1.
INFO 2024-07-24 17:43:16,774 sim_trace - Customer arrival is modeled by Poisson distribution.
INFO 2024-07-24 17:43:16,774 sim_trace - The distribution parameters are [1].
INFO 2024-07-24 17:43:16,775 sim_trace - Per customer demand is modeled using Uniform distribution.
INFO 2024-07-24 17:43:16,775 sim_trace - parameters are: [1, 3]
INFO 2024-07-24 17:43:16,775 sim_trace - Supply chain performance:

INFO 2024-07-24 17:43:16,776 sim_trace - : 0.0000: (Customer 1): ordering 7 units from retailer1.
INFO 2024-07-24 17:43:16,776 sim_trace - : 0.0000: (Customer 1): ordering 3 units from man1.
INFO 2024-07-24 17:43:16,778 sim_trace - : 0.0000: (Customer 1): got 7 units from retailer1.
INFO 2024-07-24 17:43:16,778 sim_trace - : 0.0000: (Customer 1): got 3 units from man1.
INFO 2024-07-24 17:43:16,779 sim_trace - : 0.1399: (Customer 2): ordering 3 units from man1.
INFO 2024-07-24 17:43:16,779 sim_trace - : 0.1399: (Customer 2): got 3 units from man1.
INFO 2024-07-24 17:43:16,780 sim_trace - : 0.3883: (Customer 3): ordering 2 units from man1.
INFO 2024-07-24 17:43:16,780 sim_trace - : 0.3883: (Customer 3): got 2 units from man1.
INFO 2024-07-24 17:43:16,781 sim_trace - : 0.4136: (Customer 2): ordering 9 units from retailer1.
INFO 2024-07-24 17:43:16,782 sim_trace - : 0.4136: (Customer 2): got 9 units from retailer1.
INFO 2024-07-24 17:43:16,783 sim_trace - : 0.4595: (Customer 3): ordering 1 units from retailer1.
INFO 2024-07-24 17:43:16,783 sim_trace - : 0.4595: (Customer 3): got 1 units from retailer1.
INFO 2024-07-24 17:43:16,783 sim_trace - : 0.6917: (Customer 4): ordering 2 units from retailer1.
INFO 2024-07-24 17:43:16,785 sim_trace - : 0.6917: (Customer 4): got 2 units from retailer1.
INFO 2024-07-24 17:43:16,785 sim_trace - : 0.7288: (Customer 5): ordering 6 units from retailer1.
INFO 2024-07-24 17:43:16,785 sim_trace - : 0.7288: (Customer 5): got 6 units from retailer1.
INFO 2024-07-24 17:43:16,786 sim_trace - : 0.8044: (Customer 4): ordering 3 units from man1.
INFO 2024-07-24 17:43:16,786 sim_trace - : 0.8044: (Customer 4): got 3 units from man1.
INFO 2024-07-24 17:43:16,788 sim_trace - : 1.0000: (124): inventory level = 589.
INFO 2024-07-24 17:43:16,788 sim_trace - : 1.0000: (125): inventory level = 275.
INFO 2024-07-24 17:43:16,788 sim_trace - : 1.0634: (Customer 6): ordering 6 units from retailer1.
INFO 2024-07-24 17:43:16,789 sim_trace - : 1.0634: (Customer 6): got 6 units from retailer1.
INFO 2024-07-24 17:43:16,789 sim_trace - : 1.5257: (Customer 7): ordering 3 units from retailer1.
INFO 2024-07-24 17:43:16,790 sim_trace - : 1.5257: (Customer 7): got 3 units from retailer1.
INFO 2024-07-24 17:43:16,790 sim_trace - : 1.6137: (Customer 5): ordering 1 units from man1.
INFO 2024-07-24 17:43:16,790 sim_trace - : 1.6137: (Customer 5): got 1 units from man1.
INFO 2024-07-24 17:43:16,790 sim_trace - : 1.6271: (Customer 8): ordering 10 units from retailer1.
INFO 2024-07-24 17:43:16,791 sim_trace - : 1.6271: (Customer 8): got 10 units from retailer1.
INFO 2024-07-24 17:43:16,791 sim_trace - : 1.6445: (Customer 9): ordering 1 units from retailer1.
INFO 2024-07-24 17:43:16,791 sim_trace - : 1.6445: (Customer 9): got 1 units from retailer1.
INFO 2024-07-24 17:43:16,791 sim_trace - : 1.7474: (Customer 10): ordering 2 units from retailer1.
INFO 2024-07-24 17:43:16,792 sim_trace - : 1.7474: (Customer 10): got 2 units from retailer1.
INFO 2024-07-24 17:43:16,792 sim_trace - : 1.7497: (Customer 11): ordering 4 units from retailer1.
INFO 2024-07-24 17:43:16,792 sim_trace - : 1.7497: (Customer 11): got 4 units from retailer1.
INFO 2024-07-24 17:43:16,793 sim_trace - : 1.9797: (Customer 12): ordering 1 units from retailer1.
INFO 2024-07-24 17:43:16,793 sim_trace - : 1.9797: (Customer 12): got 1 units from retailer1.
INFO 2024-07-24 17:43:16,794 sim_trace - : 2.0000: (124): inventory level = 588.
INFO 2024-07-24 17:43:16,794 sim_trace - : 2.0000: (125): inventory level = 248.
INFO 2024-07-24 17:43:16,794 sim_trace - : 2.1268: (Customer 13): ordering 10 units from retailer1.
INFO 2024-07-24 17:43:16,795 sim_trace - : 2.1268: (Customer 13): got 10 units from retailer1.
INFO 2024-07-24 17:43:16,795 sim_trace - : 2.3093: (Customer 14): ordering 9 units from retailer1.
INFO 2024-07-24 17:43:16,795 sim_trace - : 2.3093: (Customer 14): got 9 units from retailer1.
INFO 2024-07-24 17:43:16,796 sim_trace - : 2.9855: (Customer 6): ordering 3 units from man1.
INFO 2024-07-24 17:43:16,796 sim_trace - : 2.9855: (Customer 6): got 3 units from man1.
INFO 2024-07-24 17:43:16,797 sim_trace - : 3.0000: (124): inventory level = 585.
INFO 2024-07-24 17:43:16,798 sim_trace - : 3.0000: (125): inventory level = 229.
INFO 2024-07-24 17:43:16,799 sim_trace - : 3.0486: (Customer 15): ordering 7 units from retailer1.
INFO 2024-07-24 17:43:16,800 sim_trace - : 3.0486: (Customer 15): got 7 units from retailer1.
INFO 2024-07-24 17:43:16,801 sim_trace - : 3.0969: (Customer 16): ordering 4 units from retailer1.
INFO 2024-07-24 17:43:16,801 sim_trace - : 3.0969: (Customer 16): got 4 units from retailer1.
INFO 2024-07-24 17:43:16,802 sim_trace - : 3.1938: (Customer 17): ordering 1 units from retailer1.
INFO 2024-07-24 17:43:16,803 sim_trace - : 3.1938: (Customer 17): got 1 units from retailer1.
INFO 2024-07-24 17:43:16,804 sim_trace - : 3.6337: (Customer 18): ordering 2 units from retailer1.
INFO 2024-07-24 17:43:16,804 sim_trace - : 3.6337: (Customer 18): got 2 units from retailer1.
INFO 2024-07-24 17:43:16,805 sim_trace - : 3.7353: (Customer 19): ordering 6 units from retailer1.
INFO 2024-07-24 17:43:16,805 sim_trace - : 3.7353: (Customer 19): got 6 units from retailer1.
INFO 2024-07-24 17:43:16,805 sim_trace - : 3.7571: (Customer 20): ordering 10 units from retailer1.
INFO 2024-07-24 17:43:16,805 sim_trace - : 3.7571: (Customer 20): got 10 units from retailer1.
INFO 2024-07-24 17:43:16,806 sim_trace - : 3.8512: (Customer 21): ordering 4 units from retailer1.
INFO 2024-07-24 17:43:16,806 sim_trace - : 3.8512: (Customer 21): got 4 units from retailer1.
INFO 2024-07-24 17:43:16,806 sim_trace - : 3.9273: (Customer 22): ordering 5 units from retailer1.
INFO 2024-07-24 17:43:16,806 sim_trace - : 3.9273: (Customer 22): got 5 units from retailer1.
INFO 2024-07-24 17:43:16,807 sim_trace - : 4.0000: (124): inventory level = 585.
INFO 2024-07-24 17:43:16,807 sim_trace - : 4.0000: (125): inventory level = 190.
INFO 2024-07-24 17:43:16,807 sim_trace - : 4.2684: (Customer 7): ordering 2 units from man1.
INFO 2024-07-24 17:43:16,807 sim_trace - : 4.2684: (Customer 7): got 2 units from man1.
INFO 2024-07-24 17:43:16,808 sim_trace - : 4.3855: (Customer 23): ordering 8 units from retailer1.
INFO 2024-07-24 17:43:16,808 sim_trace - : 4.3855: (Customer 23): got 8 units from retailer1.
INFO 2024-07-24 17:43:16,808 sim_trace - : 4.5888: (Customer 24): ordering 8 units from retailer1.
INFO 2024-07-24 17:43:16,809 sim_trace - : 4.5888: (Customer 24): got 8 units from retailer1.
INFO 2024-07-24 17:43:16,809 sim_trace - : 4.7026: (Customer 25): ordering 1 units from retailer1.
INFO 2024-07-24 17:43:16,809 sim_trace - : 4.7026: (Customer 25): got 1 units from retailer1.
INFO 2024-07-24 17:43:16,810 sim_trace - : 4.7171: (Customer 26): ordering 3 units from retailer1.
INFO 2024-07-24 17:43:16,810 sim_trace - : 4.7171: (Customer 26): got 3 units from retailer1.
INFO 2024-07-24 17:43:16,810 sim_trace - : 4.7298: (Customer 8): ordering 2 units from man1.
INFO 2024-07-24 17:43:16,811 sim_trace - : 4.7298: (Customer 8): got 2 units from man1.
INFO 2024-07-24 17:43:16,811 sim_trace - : 4.8359: (Customer 9): ordering 3 units from man1.
INFO 2024-07-24 17:43:16,811 sim_trace - : 4.8359: (Customer 9): got 3 units from man1.
INFO 2024-07-24 17:43:16,812 sim_trace - : 4.9682: (Customer 27): ordering 5 units from retailer1.
INFO 2024-07-24 17:43:16,812 sim_trace - : 4.9682: (Customer 27): got 5 units from retailer1.
INFO 2024-07-24 17:43:16,813 sim_trace - *** SC stats ***
INFO 2024-07-24 17:43:16,813 sim_trace - Number of products sold = 157
INFO 2024-07-24 17:43:16,813 sim_trace - SC total profit = 15700
INFO 2024-07-24 17:43:16,815 sim_trace - SC total tranportation cost = 0
INFO 2024-07-24 17:43:16,815 sim_trace - SC inventory cost = 9620
INFO 2024-07-24 17:43:16,816 sim_trace - SC revenue (profit - cost) = 6080
INFO 2024-07-24 17:43:16,816 sim_trace - Average revenue (per day) = 1216.0
INFO 2024-07-24 17:43:16,816 sim_trace - Customers returned  = 0
```
</div>