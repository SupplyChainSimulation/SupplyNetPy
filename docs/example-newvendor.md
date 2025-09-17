<style>
    img{
        width:70%;
    }
</style>

# News Vendor Problem

This example illustrates how to model and simulate the classic **newsvendor problem**. In this problem, a decision-maker must determine the optimal order quantity for a perishable product with uncertain demand, aiming to maximize expected profit by balancing the risks of overstocking and understocking. 

## Problem Definition

The newsvendor orders Q units every day. Each unit costs c, and the selling price is p. The newsvendor faces normally distributed demand with mean &mu; and standard deviation &sigma;. If, on a certain day, the actual demand is k, then the net profit after selling k units is calculated as:

<span>
    <strong>Profit</strong> = <strong>Revenue</strong> &minus; <strong>Order Cost</strong> = <em>k</em> &times; <em>p</em> &minus; <em>Q</em> &times; <em>c</em>
</span>

However, if there are any units left unsold at the end of the day, they are considered wastage since they cannot be sold the next day. The newsvendor can sell these unsold units back to the supplier at a lower price, called the salvage value s. If the actual demand that day is less than the order size Q, then the net profit is thus calulated as:

<span>
    <strong>Profit</strong> = <strong>Revenue</strong> + <strong>Salvage</strong> &minus; <strong>Order Cost</strong> = <em>k</em> &times; <em>p</em> + (<em>Q</em> &minus; <em>k</em>) &times; <em>s</em> &minus; <em>Q</em> &times; <em>c</em>
</span>

When the actual demand <em>k</em> exceeds the newsvendor's order quantity <em>Q</em>, the profit is calculated as:

<span>
    <strong>Profit</strong> = <em>Q</em> &times; <em>p</em> &minus; <em>Q</em> &times; <em>c</em>
</span> 
&emsp; &emsp; (In this case, all available units are sold, and the profit is based on the total revenue from selling <em>Q</em> units minus the total ordering cost.)

So, the newsvendor problem is defined by following parameters.

- **Ordering cost (c)**: Cost per unit ordered.
- **Selling price (p)**: Price per unit sold.
- **Salvage value (s)**: Value per unsold unit at the end of the period.
- **Mean demand (&mu;)**: Average demand during the period.
- **Standard deviation of demand (&sigma;)**: Demand variability.
- **Number of samples (n)**: Number of demand samples for simulation.
- **Order quantity (Q)**: Quantity ordered for the period.

The objective is to find the order quantity Q<sup>*</sup> that maximizes expected profit.

## Analytical Solution

The optimal order quantity is given by:

<span>
    Q<sup>*</sup> = &mu; + &sigma; &middot; &Phi;<sup>&minus;1</sup>
    (<span style="vertical-align:middle;">C<sub>u</sub> / (C<sub>u</sub> + C<sub>o</sub>)</span>)
</span>

where:

- C<sub>u</sub> = p - c: Underage cost (profit lost per unit of unmet demand)
- C<sub>o</sub> = c - s: Overage cost (cost per unsold unit)
- &Phi;<sup>-1</sup>: Inverse standard normal 
- C<sub>u</sub>/(C<sub>u</sub> + C<sub>o</sub>): Critical ratio (proportion of demand to satisfy)

## Example Parameters

Given:<br>
  c = 2<br>
  p = 5<br>
  s = 1<br>
  &mu; = 100<br>
  &sigma; = 15<br>
  n = 1000<br>
  Q = 100 (example order quantity)<br>

Plugging in the values:<br>
C<sub>u</sub> = 5 - 2 = 3<br>
C<sub>o</sub> = 2 - 1 = 1<br>
Critical ratio = 3/(3 + 1) = 0.75<br>
Q<sup>*</sup> = 100 + 15 &middot; &Phi;<sup>-1</sup>(0.75)<br>
Q<sup>*</sup> &approx; 100 + 15 &middot; 0.6745 = 110.12<br>
So, the optimal order quantity is approximately **110 units**.<br>

## Modeling and Simulating the Newsvendor Problem

It is a simple three-node supply chain with one supplier, a newsvendor (retailer), and normally distributed demand at the newsvendor.

![Newsvendor](img/newsvendor.png)

**Simulation Setup:**

- An *infinite\_supplier* is used to ensure unlimited supply to the newsvendor.
- The focus of the simulation is on the newsvendor node `newsvendor1`, which:
    - Maintains perishable inventory with a shelf life of 1 day. (Shelf life is set to value 1.00001 to avoid expiration before daily consumption.)
    - Uses a periodic replenishment policy, ordering every day.
- The link between the supplier and the newsvendor has a lead time of 0, meaning orders are delivered immediately each day.
- Demand is modeled as a normal distribution. The `normal_quantity()` function samples order sizes from this distribution.
- Setting `consume_available` flag to True for demand allows partial fulfillment. This is necessary because, in the simulation model, the demand appears as a single order of Q units, but in reality, these are individual customers purchasing newspapers.
- This setup ensures that the simulation accurately represents the intended demand and fulfillment process for the newsvendor problem.



```python
{% include "../examples/py/newsvendor.py" %}
```

The following plot shows the relationship between profit and order quantity (Q). The curve clearly indicates that the maximum profit is achieved when Q is approximately 110, confirming the analytical solution for the optimal order quantity.

![alt text](img/img_newsvendor_Q.png)


## Takeway

This example demonstrated how to solve the newsvendor problem using simulation-based approaches using SupplyNetPy library. By simulating different order quantities and evaluating the resulting profits, we can visualize and confirm the optimal order quantity that maximizes expected profit. This approach can be extended to more complex inventory scenarios and demand distributions, providing valuable insights for inventory management decisions.
