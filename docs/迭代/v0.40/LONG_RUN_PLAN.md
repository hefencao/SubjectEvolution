# v0.40 D2-B paired audit plan

## Source runs

Reuse the completed v0.39 3000-tick runs and their exact checkpoints. D2-B does
not require rerunning the source trajectory because leave-one-out interventions
start from trusted checkpoints and the new ordinary-run contribution fields are
not required to execute the branches.

Recommended phases:

```text
peak,trough
```

Recommended horizon:

```text
120 ticks initially; 300 ticks for any effect that survives the first screen
```

## Execute

```bash
se-d2-audit \
  --run-dir runs/d2a_contextual_modules_multiseed/seed_10001 \
  --run-dir runs/d2a_contextual_modules_multiseed/seed_10002 \
  --run-dir runs/d2a_contextual_modules_multiseed/seed_10003 \
  --output analyses/d2b_module_audit_120 \
  --phases peak,trough \
  --horizon 120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

For branches with non-zero downstream effects:

```bash
se-d2-audit \
  --plan analyses/d2b_module_audit_120/d2_module_audit_plan.json \
  --output analyses/d2b_module_audit_repeat \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

To extend the horizon, regenerate a plan from the same run directories with
`--horizon 300` so the `until_tick` values are updated explicitly.

## Primary outcomes

- alive, energy, births and deaths;
- resource-environment effective dimensions;
- requested and realized harvest-share dimensions;
- extraction efficiency;
- effective lineages and largest-lineage fraction;
- functional preference and residual magnitude;
- contribution effective count, dominance and cancellation;
- effective transferred knowledge roots.

## Stop conditions

Remain at D2-B when:

- all downstream effects are near zero despite structural expression;
- one module contributes almost all isolated residual across seeds;
- effects are only maintenance-cost refunds;
- effects disappear at the longer horizon;
- effective lineage count remains near one or two, preventing repeated
  evolutionary evidence.

Only after passing the gate should D2-C consider duplication/deletion or more
physical output ports.
