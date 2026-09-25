# 7. Evaluation, Testing & Future Scope

## 7.1 Success Metrics

| Metric | Target / Purpose |
|---|---|
| Recommendation accuracy vs. domain-expert judgment | Measured on a held-out set of expert-labeled commodity/material pairs |
| Shelf-life prediction error (MAE, days) | Compared against literature/pilot ground truth |
| Recommendation latency | Sub-second for cached/common commodities, few seconds for cold ML inference |
| User adoption in pilot | # of active users, # of recommendations acted upon |
| Feedback capture rate | % of recommendations that receive a follow-up outcome/feedback entry |

## 7.2 Testing Strategy

- **Unit tests** per agent (given a fixed input, does the rule/model return the expected band/category?).
- **Golden-set regression tests**: a curated set of known commodity/environment combinations with expert-agreed correct recommendations — run on every model/rule change to catch regressions.
- **Boundary/edge-case tests**: extreme inputs (e.g., very high respiration rate + frozen storage — a genuinely rare/contradictory combination) should degrade gracefully with a clear explanation rather than fail silently.
- **Domain-expert review cycle**: periodic manual audit of a random sample of live recommendations, especially before and after any knowledge-base or model update.

## 7.3 Risk Considerations

- **Food-safety implication of a wrong recommendation**: since a bad packaging suggestion could contribute to spoilage/health risk, the system should be positioned explicitly as a *decision-support* tool, not a certified/regulatory substitute — recommendations should carry a disclaimer to that effect, and high-stakes commodities (e.g., ready-to-eat, meat/dairy) should route through stricter rule-based bounds with lower ML-driven flexibility.
- **Knowledge base staleness**: packaging material properties and MAP recipes should have a review cadence (e.g., every 6–12 months) as materials and standards evolve.
- **Data scarcity for ML models**: many commodities will have little to no historical feedback data initially — the rule-based fallback (Phase 2) exists precisely to keep the system useful before enough data accumulates for reliable ML predictions.

## 7.4 Future Scope

1. **Sustainability analysis**: full life-cycle assessment (LCA) scoring per material, not just a static recyclable/biodegradable flag.
2. **Cost optimization**: live integration with vendor/material pricing feeds for a true cost-per-unit-shelf-life-day comparison.
3. **QR-based traceability**: attach a QR code at the packaging-recommendation stage that follows the batch through the supply chain, feeding real outcome data back into the feedback store automatically.
4. **IoT integration**: in-package humidity/gas sensors feeding real-time spoilage signals back into the shelf-life model for continuous validation.
5. **Mobile-first field tool**: a lightweight Flutter app for farmers/FPOs to get quick recommendations on-site, with offline-capable rule-engine fallback when connectivity is poor.
6. **Multi-language support**: given the target users include farmers and small local manufacturers, localized language support for the input form and explanations would materially widen adoption.
