### Utilities

__Functions:__

| Name | Description |
| --- | --- |
| create_sc_nodes | Creates a specified number of nodes of a given node type in the supply chain. |
| create_sc_links | Creates links from each node in `from_nodes` list to every other node in `to_nodes` list. |
| create_random_sc_net | This function creates a fully connected random supply chain network. |
| get_sc_net_info | Get supply chain network information.  |
| visualize_sc_net | Visualize the supply chain network as a graph. |
| simulate_sc_net | Simulate the supply chain network for a given time period. |
| create_sc_net | Create a supply chain network. |

##### create_sc_nodes
`create_sc_nodes(num_of_nodes, node_type, inv_cap_bounds, inv_hold_cost_bounds, inv_reorder_lvl_bounds, product=default_product, env=env)`
:::SupplyNetPy.Components.utilities.create_sc_nodes

##### create_sc_links
`create_sc_links(from_nodes, to_nodes, lead_time_bounds, tranport_cost_bounds)`
:::SupplyNetPy.Components.utilities.create_sc_links

##### create_random_sc_net
`create_random_sc_net(num_suppliers, num_manufacturers, num_distributors, num_retailers, env=env, product=default_product)`
:::SupplyNetPy.Components.utilities.create_random_sc_net

##### get_sc_net_info
`get_sc_net_info(supplychainnet)`
:::SupplyNetPy.Components.utilities.get_sc_net_info

##### visualize_sc_net
`visualize_sc_net(supplychainnet) `
:::SupplyNetPy.Components.utilities.visualize_sc_net

##### simulate_sc_net
`simulate_sc_net(supplychainnet, sim_time, env=env)`
:::SupplyNetPy.Components.utilities.simulate_sc_net

##### create_sc_net
`create_sc_net(nodes:list = [],links:list = [],demands:list = [],products:list = [])`
:::SupplyNetPy.Components.utilities.create_sc_net