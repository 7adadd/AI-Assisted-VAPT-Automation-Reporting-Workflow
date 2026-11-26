# Validation Log Template — AI-Assisted VAPT Workflow

> Principle: An AI claim is not a finding. Every AI output used passes L1 (Data-verified), L2 (Lab-executed, if executable), L3 (Cross-model, if high-impact), and L4 (Human/Peer QA for final report).

| ID | Phase | AI Claim / Output | Model | Source Cited | Ground Truth Check | Result | Verdict |
|---|---|---|---|---|---|---|---|
| W2-001 | AD | Example claim | qwen2.5:3b | [bh:edge E01] | Verified vs BFS/BloodHound | Confirmed | ✅ L1+L3 |

## Weekly Accuracy Summary Formula
- Total AI claims evaluated: `N`
- Verified (`✅`): `V (V/N %)`
- Partially correct (`⚠️`): `P (P/N %)`
- Hallucinations / Rejected (`❌`): `H (H/N %)`
- Unknown / Insufficient data (`❔`): `U`
