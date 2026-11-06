# Proofs

`ProofReceipt` lets a check record its last run in `docs/proofs/<name>.txt`: passed or failed, when, and its report. The unity-dev Stop hook compares these with what changed since, and a review reads them. A receipt is written by the check, so it can't drift from what ran.

- **Destination:** `Core/Proofs/`
- **Depends on:** nothing.

```csharp
ProofReceipt.Write("locomotion-visitor", passed, report);
```

The name starts with the check's family, which is how the hook matches a receipt to the files that can make it old: `architecture`, `ui-*`, `scene-cost-*`, `off-screen-*`, `budgets-*`, `locomotion-*`, `crowd-*`, `balance-*`. The Blender scripts write theirs through their `PROOF_DIR` setting: `validate_mesh-*`, `inspect_character-*`, `inspect_animation-*`, `study-*`. A family the project has no use for goes in `docs/proofs/not-applicable.txt`, as `family: reason`, and a failing receipt the user accepted, as `receipt-name: their words`.

Call it before the test's assertion, so a failing run leaves a failing receipt. In a player it does nothing.
