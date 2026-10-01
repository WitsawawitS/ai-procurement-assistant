# Calculation methodology

All cost arithmetic uses Python `Decimal`. Output amounts are rounded half-up to two decimals. Scores are ranked before display rounding; rounded cost components may differ from the rounded total by a small rounding amount. User interface amounts use THB.

## 1. Quantity

`ordered quantity = ceil(max(required quantity, MOQ) / pack size) × pack size`

All quantities and lead times must be positive integers. Capacity is checked against **ordered**, not required, quantity. Excess quantity is reported; the model does not assume it will be sold or consumed later.

## 2. Currency and cost scope

FX is expressed as **THB per one unit of quote currency**. The THB rate is exactly one. Every amount in a quote (unit price, freight, insurance and other cost) uses that quote's currency.

- Goods = unit price × ordered quantity × FX
- Freight, insurance and other cost = respective per-shipment amount × FX
- Customs base in this illustrative model = goods + freight + insurance
- Duty = customs base × input duty percentage / 100
- VAT = (customs base + duty) × input VAT percentage / 100
- Net cost before VAT = customs base + duty + other cost
- Cash outlay = net cost before VAT + VAT
- Ranked landed cost = net cost before VAT, plus VAT only when non-recoverable
- Cost per required unit = ranked landed cost / required quantity
- Cost per ordered unit = ranked landed cost / ordered quantity

Tax rates are user-specified **scenario inputs**. The sample 5% / 7% assumptions are not a statement of legally applicable rates. Other costs are treated as outside the simplified VAT/duty base. Actual valuation and tax treatment require separate verification.

Freight and insurance are **incremental buyer-paid charges**. For example, if freight is already included in the quoted unit price, the buyer must not enter it again. Incoterms do not automatically allocate costs or tax responsibility. CIF, CIP, CFR and DDP labels generate a double-counting reminder. No Incoterm is inferred from country.

## 3. Eligibility gates

The following must all pass:

1. Ordered quantity ≤ declared available supplier capacity.
2. Lead days ≤ required deadline.
3. Quality percentage ≥ minimum quality.
4. OTIF percentage ≥ minimum OTIF.
5. Quote valid-until date ≥ evaluation date (expiry date is inclusive).

No eligible quote means **no award recommended**. Excluded suppliers retain visible cost breakdowns for investigation but have no score or rank. Unverified price/performance data remains the buyer's responsibility.

## 4. Weighted score

Scores are calculated only within the eligible comparison set:

- Cost score = minimum eligible landed cost / this landed cost × 100.
- Lead score = minimum eligible lead days / this lead days × 100.
- Quality score = the input quality percentage.
- Reliability score = the input OTIF percentage.
- Total score = sum of each component × its weight / 100.

Weights must be nonnegative and total exactly 100. There is no learned ranking model and no hidden risk penalty. Sort order is eligibility first, unrounded score descending, unrounded cost ascending, then quote ID ascending. Scores are conditional on the candidate set and are not an absolute supplier certification.

## 5. Baseline comparison

`baseline difference = selected baseline landed cost − recommended landed cost`

Positive means lower modeled cost than the baseline; negative means higher. The baseline may be ineligible, so the difference is a scenario comparison and not guaranteed achievable savings. No baseline or no winner means no difference is reported. Default baseline Q001 is the current local-supplier comparison assumption, not proof of a real incumbent relationship.

## 6. Scenario lab

Six independent cases are evaluated from the same successfully analyzed inputs. No scenario changes are cumulatively applied:

| Case | Change |
|---|---|
| Base | None |
| Demand −25% | Floor quantity × 0.75, minimum 1 |
| Demand +25% | Ceil quantity × 1.25, maximum 1,000,000 |
| Foreign FX +10% | Every foreign rate × 1.1; THB unchanged |
| Deadline −7 days | Deadline minus 7, minimum 1 |
| Cost-first | Weights 75 cost / 10 lead / 10 quality / 5 reliability |

Eligibility and cost are recomputed for every case. Caps follow the same validation limits as the base model. This is a deterministic stress test, not a probability forecast or optimization over all possible allocations.

## Not modeled

Split awards, inventory holding costs, working capital, payment terms, rebates, defect replacement costs, freight tiers, FX hedging, tariff classification, preferential origin, excise, taxes on miscellaneous fees, customs delays and differing technical specifications are out of scope. A single shipment and one SKU are compared at a time. Do not describe this system as an ERP, autonomous buyer or production procurement platform.
