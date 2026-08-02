# Design boundary

## Fixed bootstrap

Eight generic Subject VM nodes and one delayed edge are installed into the lowest stable subject IDs at the quiescent shared-checkpoint boundary. The profile is versioned and hashed in checkpoint lineage. No topology mutation or selection claim is made.

## Pairing

Guarded-live and read-only-control branches share the same checkpoint and random stream. Control reservations mirror live pending-target and window admission without mutating parameters or charging live-write costs.

## Export boundary

After the configured semantic horizon, no more ticks are executed. Remaining temporary writes are restored, and control reservations are released through the same exact CAS rollback owner. Incomplete windows are not promoted into evidence.

## Forbidden conclusions

No scalar objective, automatic keep/revert, permanent retention, causal authorization, learning claim, attention optimality claim or subjecthood claim is produced.
