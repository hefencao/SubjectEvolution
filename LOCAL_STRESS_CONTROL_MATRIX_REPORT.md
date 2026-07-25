# Local Stress Control Matrix Report

## 120-tick validation

| Run | Alive | Strategy dims | Cohesion | Transfer commits | Population CV | Mortality CV | Max local/global mortality |
|---|---:|---:|---:|---:|---:|---:|---:|
| v019_final_local_10001_a | 430 | 65.5086 | 0.2745 | 89 | 0.3072 | 1.4103 | 20.5556 |
| v019_final_local_10002 | 419 | 62.4441 | 0.3140 | 75 | 0.3206 | 1.8282 | 11.5091 |

The two seeds show substantial local heterogeneity despite smooth global growth. Local mortality/cohesion correlations are not directionally stable in this short sample.

## 1500-tick transfer/no-transfer endpoint means

| Condition | Alive | Effective lineages | Strategy dims | Entropy | Cohesion | Affinity dims |
|---|---:|---:|---:|---:|---:|---:|
| costed_transfer | 1356.67 | 19.8283 | 17.5670 | 1.7372 | 0.3967 | 2.4633 |
| no_transfer | 1353.00 | 20.6045 | 18.4596 | 1.7389 | 0.4051 | 2.5387 |

Short local runs validate measurement and determinism only. They do not establish that local pressure causes cohesion.
