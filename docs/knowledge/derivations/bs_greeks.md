# Black-Scholes Greeks Derivation

**Tier**: L2 (Full Derivation)
**Domain**: Options Pricing
**Prerequisites**: Basic calculus, BS formula

---

## Black-Scholes Formula

For a European call option:

$$C = S \cdot N(d_1) - K \cdot e^{-rT} \cdot N(d_2)$$

Where:
- $d_1 = \frac{\ln(S/K) + (r + \sigma^2/2)T}{\sigma\sqrt{T}}$
- $d_2 = d_1 - \sigma\sqrt{T}$
- $N(\cdot)$ is the standard normal CDF

---

## Delta ($\Delta$)

**Definition**: Rate of change of option value with respect to underlying price.

$$\Delta_{call} = \frac{\partial C}{\partial S} = N(d_1)$$

$$\Delta_{put} = \frac{\partial P}{\partial S} = N(d_1) - 1$$

**Range**:
- Call: $0 \leq \Delta \leq 1$
- Put: $-1 \leq \Delta \leq 0$

**Interpretation**: Number of shares to hold for delta-neutral hedge.

---

## Gamma ($\Gamma$)

**Definition**: Rate of change of delta with respect to underlying price.

$$\Gamma = \frac{\partial^2 C}{\partial S^2} = \frac{n(d_1)}{S \cdot \sigma \cdot \sqrt{T}}$$

Where $n(\cdot)$ is the standard normal PDF.

**Properties**:
- Always positive for long options
- Maximum at ATM
- Decreases as time to expiry increases (for ATM)

---

## Vega ($\mathcal{V}$)

**Definition**: Rate of change of option value with respect to volatility.

$$\mathcal{V} = \frac{\partial C}{\partial \sigma} = S \cdot n(d_1) \cdot \sqrt{T}$$

**Note**: Same for calls and puts.

**Units**: Price change per 1% change in volatility.

---

## Theta ($\Theta$)

**Definition**: Rate of change of option value with respect to time.

$$\Theta_{call} = -\frac{S \cdot n(d_1) \cdot \sigma}{2\sqrt{T}} - r \cdot K \cdot e^{-rT} \cdot N(d_2)$$

$$\Theta_{put} = -\frac{S \cdot n(d_1) \cdot \sigma}{2\sqrt{T}} + r \cdot K \cdot e^{-rT} \cdot N(-d_2)$$

**Units**: Price change per day (typically quoted as daily).

**Time decay**: Usually negative for long options (value decreases as expiry approaches).

---

## Rho ($\rho$)

**Definition**: Rate of change of option value with respect to risk-free rate.

$$\rho_{call} = K \cdot T \cdot e^{-rT} \cdot N(d_2)$$

$$\rho_{put} = -K \cdot T \cdot e^{-rT} \cdot N(-d_2)$$

---

## Validation Test Cases

| Greek | S=100, K=100, T=1, r=0.05, σ=0.20 | Expected |
|-------|-----------------------------------|----------|
| Delta (Call) | - | 0.6368 |
| Gamma | - | 0.0188 |
| Vega | - | 37.52 |
| Theta (Call) | - | -6.41 (annual) |
| Rho (Call) | - | 53.23 |

**Validator**: financepy, pyfeng

---

## References

- Hull, J.C. (2018). Options, Futures, and Other Derivatives
- Wilmott, P. (2006). Paul Wilmott on Quantitative Finance
