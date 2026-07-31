# Design

## Problem

D1-L correctly stopped two qualification seeds at tick 240. Final populations
were 84 and 88 from 160 founders, but only 9 and 14 descendants remained alive.
The legacy reproduction rule debited 0.6 energy from the parent while giving the
newborn only 45% of that amount. The resulting hidden loss makes descendant
survival a poor substrate property and prevents later combination-dependent
genes from receiving a fair maturation window.

## D1-M boundary

D1-M adds no inherited trait. It replaces the legacy dissipative newborn rule
with one fixed conservative transfer shared by every entity:

- event overhead: 0.1 energy;
- newborn endowment: 0.9 energy;
- required parent reserve after the event: 0.8 energy;
- total eligibility requirement: 1.8 energy.

The same full architecture remains active, so qualification includes existing
sensor, storage, conversion, physiology and knowledge costs. Resource throughput
and base maintenance are calibrated before any new gene is attached.

## Authorization

The three-seed source panel must pass all tick-120, tick-240 and tick-360 health
checkpoints. No paired branch, new inherited capability or longer evolutionary
panel is authorized by configuration existence alone.
