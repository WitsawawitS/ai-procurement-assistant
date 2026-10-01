# Quote data dictionary

UTF-8 CSV, at most 500 KB and 50 rows. Header names and order must match the sample. Quote IDs must be unique across all products. Text fields are 1–100 characters without control characters. Numeric fields must be finite; percentages accept 0–100. No missing values are imputed.

| Column | Type / unit | Meaning |
|---|---|---|
| id | Text | Unique quote identifier |
| name | Text | Supplier display name |
| country | Text | Informational country label |
| sku | Text | Product identifier; match only technically equivalent items and unit of measure |
| currency | Enum | THB, USD, EUR, JPY, CNY, GBP or SGD |
| unit_price | Positive number / quote currency | Price per unit; ≤ 1,000,000 |
| moq | Positive integer / units | Minimum order quantity |
| pack_size | Positive integer / units | Order multiple |
| freight | Nonnegative number / quote currency | Incremental cost for one shipment, not per unit |
| insurance | Nonnegative number / quote currency | Incremental shipment insurance |
| other_cost | Nonnegative number / quote currency | Other shipment costs, outside the simplified tax base |
| duty_pct | Percentage | Scenario assumption for duty |
| vat_pct | Percentage | Scenario assumption for VAT |
| lead_days | Positive integer / calendar days | Full order-to-delivery time, including production and transit |
| quality_pct | Percentage | User-provided accepted-unit quality rate |
| otif_pct | Percentage | User-provided historical on-time-in-full rate |
| capacity | Positive integer / units | Available quantity for this order |
| incoterm | Enum | EXW, FCA, FAS, FOB, CFR, CIF, CPT, CIP, DAP, DPU or DDP; label only |
| valid_until | YYYY-MM-DD | Inclusive final date for quote validity |

Numeric quote fields other than percentages have a maximum of 1,000,000. Quote lead time uses the same general numeric limit; scenario deadline is limited to 3,650 days. Scenario quantity is 1–1,000,000. FX rates are 0.000001–1,000,000 THB per currency unit; THB is fixed at 1.

The demo contains 10 offers across BRG-6205 (bearing) and FLT-H100 (industrial filter) from fictional suppliers. Long validity dates keep the demo usable; they are not realistic supplier commitments. Fixed shipment charges make sensitivity analysis illustrative, not a freight quotation.
