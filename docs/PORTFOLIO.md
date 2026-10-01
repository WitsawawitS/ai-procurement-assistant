# Portfolio and interview guide

## Project description

**AI Procurement Assistant — Supplier Comparison & Cost Analysis**

An AI-assisted portfolio project that demonstrates sourcing decision support through deterministic landed-cost calculations, constraint-based supplier evaluation, weighted ranking and scenario analysis. Python provides the calculation/API layer, SQLite stores decision snapshots, and a responsive JavaScript interface lets buyers compare and explain trade-offs. An optional OpenAI integration generates narrative explanations from the computed results.

## Resume wording (use after you can demonstrate and explain the system)

- Developed an AI-assisted procurement portfolio application to compare supplier landed costs, delivery constraints, quality and OTIF using Python, SQL/SQLite and JavaScript.
- Implemented multi-currency scenario analysis, transparent weighted scoring and reproducible decision snapshots, validated against synthetic sourcing cases.

Do not claim real cost savings, actual supplier negotiations, commercial deployment or independently handwritten code if those are not true. The optional AI adapter exists, but initial validation used mocked API responses rather than a paid live model call.

## 60-second explanation

“I designed this project around a procurement problem: the lowest unit price can be misleading once MOQ, shipping, currency and delivery requirements are considered. The app converts quotes into comparable landed costs, removes infeasible options, and ranks the remaining suppliers using explicit business priorities. I can test how the choice changes when demand or FX changes. Python computes the figures; AI is optional and only helps explain them. The dataset is synthetic, so I present the results as modeled scenarios, not real savings.”

## Questions to prepare

1. Why separate cash outlay from recoverable VAT in the comparison cost?
2. How can MOQ and pack size change the apparent cheapest offer?
3. Why filter infeasible suppliers before weighting their price?
4. Why is Decimal used, and when does rounding happen?
5. How does the formula react when weights or candidates change?
6. What data is stored in SQLite, and why use parameterized queries?
7. What does a checksum prove—and what does it not prove?
8. Why does AI not control the ranking or place orders?
9. How are user data, HTML/CSV exports and API keys handled?
10. What would need to change for a production, multi-user deployment?

## Extension ideas for a future version

Only claim these when implemented: historical order/delivery data integration, observed OTIF calculation, split-award optimization, freight tiers, contract/payment terms, inventory holding cost, authenticated multi-user access, live FX with timestamped sources, and deployment behind a production server. Keep the present version's scope clear.
