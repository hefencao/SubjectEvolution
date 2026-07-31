# SE project status

Version: **0.92.0**

## Current development direction

Audit expansion and new-gene work remain paused. D1-L failed its short source
qualification after two seeds and did not run the third. v0.92 advances D1-M,
which changes only reproduction bookkeeping and substrate throughput: every
entity uses the same fixed conservative offspring endowment, so no inherited
trait is being screened.

## D1-L terminal qualification

At tick 240 the two completed D1-L seeds retain 84 and 88 entities from 160
founders. Cumulative births are 49 and 58, but only 9 and 14 descendants remain
alive. The supplied compact bundle omitted aggregate health events and the
generated config sidecar because of the v0.91 packaging bug; the final summaries
are frozen without reconstructing absent evidence. No capability or evolution
interpretation is authorized.

## v0.91 manifest and failed-result handoff fix

The generated sidecar is canonically `<config>.manifest.json`, for example
`source_config.json.manifest.json`. The generator, workflow precondition, and
result packager now use the same path. Failed health bundles include source
config, sidecar, panel index, aggregate health report, staged runtime events,
and long-run summary.

## D1-M fixed conservative substrate

The legacy rule debited 0.6 parent energy but transferred only 0.27 to the
newborn. D1-M instead uses a fixed, non-heritable conservative transfer:
0.1 event overhead, 0.9 newborn endowment, and 0.8 required parent reserve.
The total eligibility requirement is 1.8. Existing architecture costs remain
active.

The source panel uses 128 founders and preregistered tick-120, tick-240, and
tick-360 health checks. Three new independent seeds must all retain population
scale, living descendants, generation depth, founder replacement, and bounded
checkpoint decline. Internal implementation-calibration seeds are not part of
the requested evidence.

## Development-order rule

1. Qualify the non-heritable substrate on independent seeds.
2. Estimate per-capita energy throughput and reserve before attaching a gene.
3. Bound structural, use, development, and combination-maturation costs against
   that budget.
4. Re-run source health after capability attachment.
5. Only then authorize paired or evolutionary measurement.

## Current task

Run only the D1-M 360-tick qualification panel and package its full staged health
evidence. Do not add another inherited capability or create a paired branch until
all three independent seeds pass.

## Still incomplete

- repeated qualification of the D1-M turnover substrate on independent seeds;
- a formal capability-affordability budget derived from qualified throughput;
- a combination-maturation protocol;
- independent evolutionary evidence for any D1 inherited allocation;
- coexistence, reversal, and removal tests required for a niche claim.
