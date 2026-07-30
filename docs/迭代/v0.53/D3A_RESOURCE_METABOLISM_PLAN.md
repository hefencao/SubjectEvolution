# D3-A inherited resource buffering plan

Schema: `d3-resource-metabolism-plan-v1`
Seeds: `53001, 53002, 53003`
Horizon: `1500` ticks

## Pre-registered boundaries

- functional schema: `expression-gated-regulatory-resource-metabolism-v6`
- physiology schema: `transport-metabolism-messenger-tissue-resource-v4`
- single active population per seed: `True`
- pass fail gate: `False`
- raw harvest enters bounded store: `True`
- minimum conversion delay ticks: `1`
- store occupancy visible to functional operators: `True`
- inherited store capacity per channel: `True`
- inherited conversion capacity per channel: `True`
- equal channel base capacity and rate: `True`
- direct same tick body effect disabled: `True`
- store ledger terms: `['stored', 'converted', 'decayed', 'death loss', 'final living store']`
- named metabolic roles: `False`
- diversity reward or protection: `False`
- ecological role labels: `False`
- module copy number changed: `False`
