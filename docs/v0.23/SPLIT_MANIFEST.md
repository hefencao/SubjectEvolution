# subject_evolution 拆分清单

原始文件：`subject_evolution.py`（8938 行）

| 原始行范围 | 输出模块 |
|---:|---|
| 1-208 | `src/subject_evolution/backend.py` |
| 209-306 | `src/subject_evolution/cli.py` |
| 307-560 | `src/subject_evolution/config.py` |
| 561-1015 | `src/subject_evolution/control.py` |
| 1016-1186 | `src/subject_evolution/counterfactual.py` |
| 1187-1428 | `src/subject_evolution/device_state.py` |
| 1429-1541 | `src/subject_evolution/environment.py` |
| 1542-2337 | `src/subject_evolution/evolution.py` |
| 2338-2739 | `src/subject_evolution/execution.py` |
| 2740-3136 | `src/subject_evolution/gpu_environment.py` |
| 3137-3753 | `src/subject_evolution/gpu_runtime.py` |
| 3754-4445 | `src/subject_evolution/information.py` |
| 4446-4594 | `src/subject_evolution/intents.py` |
| 4595-4714 | `src/subject_evolution/interventions.py` |
| 4715-5003 | `src/subject_evolution/lifecycle.py` |
| 5004-5041 | `src/subject_evolution/metrics.py` |
| 5042-5271 | `src/subject_evolution/policy.py` |
| 5272-5518 | `src/subject_evolution/random_api.py` |
| 5519-5609 | `src/subject_evolution/reductions.py` |
| 5610-7652 | `src/subject_evolution/simulation.py` |
| 7653-8402 | `src/subject_evolution/social.py` |
| 8403-8543 | `src/subject_evolution/spatial.py` |
| 8544-8922 | `src/subject_evolution/subjects.py` |
| 8923-8935 | `src/subject_evolution/__init__.py` |
| 8936-8938 | `src/subject_evolution/__main__.py` |

## 修复说明

原文件第 5037-5041 行包含误嵌入的 PowerShell 文件合并命令，不是 Python 代码。拆分 `metrics.py` 时已删除这些行，否则模块无法通过语法解析。

## 运行

项目根目录已提供 `subject_evolution -> src/subject_evolution` 链接，因此 Linux 环境可直接运行：

```bash
python -m subject_evolution.cli --config configs/mvp_100k.json --output runs/mvp_100k_gpu --backend gpu
```

GPU 后端要求 CuPy >= 12、匹配的 CUDA runtime、可用 CUDA GPU，以及 CuPy Thrust 支持。

## v0.5.0 后续新增

- `src/subject_evolution/knowledge.py`：K1 动态知识目录、副本 arena、观察计划、传输计划和成本提交；
- `tests/test_knowledge.py`：K1 单元与语义隔离测试；
- `configs/mvp_small_k1*.json`：四条件 K1 对照；
- `PROJECT_STATUS.md`、`K1_IMPLEMENTATION.md`：实现和剩余路线；
- `scripts/run_k1_matrix.sh`：CPU 对照矩阵复现实验。

- `knowledge_policy.py` — K3 sparse local-knowledge policy residual plans and audits.

## v0.8.0 后续新增

- `src/subject_evolution/knowledge_subjects.py`：K4 知识内容谱系、候选主体图快照、边界流、成本与策略影响诊断；
- `tests/test_knowledge_k4.py`：K4 谱系、唯一宿主、内容存续、成本/边界/策略归因和纯观察兼容性测试；
- `configs/mvp_short_k4_candidates.json`：K4 30-tick 候选跟踪配置；
- `configs/mvp_short_k4_high_damage.json`：高损坏率变体谱系场景；
- `configs/mvp_short_k4_boundary.json`：群内/跨群边界流场景；
- `K4_IMPLEMENTATION.md`、`K4_CONTROL_MATRIX_REPORT.md`：实现和短周期验证说明。

## v0.9.0 additions

- `checkpointing.py`: trusted full-world `.sechk` bundle integrity and serialization.
- `replay.py`: offline continuation and paired counterfactual replay CLI.
- `tests/test_checkpoint_replay.py`: continuous/resumed and disk/in-memory branch exactness.
- `configs/mvp_short_replay.json`: 20-tick full-checkpoint validation configuration.

## v0.10.0 additions

- `latent_knowledge.py`: variable-length int16 content arena and inherited quantized L1 router.
- `tests/test_latent_knowledge.py`: variable length, deterministic routing, lineage mutation and checkpoint tests.
- `configs/mvp_short_latent_*.json`: L1 latent controls.

## v0.11.0 additions

- `latent_knowledge.py`: independent `quantized-mlp-latent-router-v1`, integer hard-tanh, retained L1 shadow prefix and exact publication diagnostics.
- `knowledge_policy.py`: sparse L1 comparison plan plus L2 saturation/clipping/hidden activity diagnostics.
- `tests/test_latent_router_mlp.py`: schema isolation, nonlinearity, determinism, audit logging and full checkpoint restore.
- `configs/mvp_short_latent_mlp_private.json` and `mvp_short_latent_mlp_exchange.json`.
- `LATENT_ROUTER_MLP_IMPLEMENTATION.md` and `LATENT_ROUTER_MLP_CONTROL_MATRIX_REPORT.md`.


## v0.12.0 additions

- `routing_cost.py`: physical routing-computation cost and all-or-none entity budget arbitration.
- `tests/test_routing_cost.py`: formula, rejection, attribution and checkpoint tests.
- `LATENT_ROUTING_COST_IMPLEMENTATION.md` and control matrix reports.


## v0.13.0 additions

- `working_memory.py`: inherited quantized four-dimensional working memory updated from public-state change and five-dimensional prediction error.
- `latent_knowledge.py`: `sparse-query-key-topk-router-v1`, stable integer query-key scoring and ephemeral Top-k worksets.
- `knowledge_policy.py` / `routing_cost.py`: per-entity selection work diagnostics and selection cost independent of nonzero residual output.
- `knowledge_subjects.py`: separate routing, selection and working-memory cost attribution.
- `tests/test_memory_selection.py`: memory, stable Top-k, K=0, cost, attribution and checkpoint tests.
- `configs/mvp_short_latent_l2_memory*.json`: 30-tick memory and Top-k control matrix.
- `WORKING_MEMORY_IMPLEMENTATION.md`, `SPARSE_KNOWLEDGE_SELECTION_IMPLEMENTATION.md`, and validation/control reports.

## v0.14.0 additions

- `config.py` / `policy.py`: optional `inherited-discrete-topk-v1` capacity schema and one inherited discrete capacity gene.
- `latent_knowledge.py`: per-entity stable Top-k capacity resolution while retaining the authoritative variable-length knowledge SoA.
- `knowledge_policy.py` / `routing_cost.py` / `knowledge.py`: requested-capacity audit fields, physical cost accounting, metrics, and CSV provenance.
- `interventions.py` / `simulation.py`: checkpointed `ablate-working-memory` and `bypass-sparse-selection` scientific module interventions.
- `tests/test_memory_selection.py`: inherited capacity mapping, genome isolation, authority preservation, ablation, and checkpoint tests.
- `configs/mvp_short_latent_l2_memory_topk_inherited.json`: 30-tick inherited-capacity validation condition.
- `EVOLVABLE_SELECTION_IMPLEMENTATION.md`, `CAUSAL_ABLATION_IMPLEMENTATION.md`, and control/validation reports.


## v0.15.0 additions

- `niches.py`: fixed-budget four-resource affinity, policy resource utility, public resource signal, five-dimensional harvest effects, and morphology diagnostics.
- `environment.py` / `gpu_environment.py`: opt-in spatially asynchronous multi-niche resource and hazard fields.
- `simulation.py` / `evolution.py`: raw four-channel harvest accounting, environment/affinity long-run metrics, checkpoint state, and manifest provenance.
- `tests/test_environment_diversity.py`: legacy isolation, fixed-budget tradeoff, environment/device parity, checkpoint and manifest tests.
- `configs/mvp_short_latent_l2_memory_topk_inherited_heterogeneous*.json`: rich, no-affinity, and energy-budget calibration conditions.
- `ENVIRONMENTAL_HETEROGENEITY_IMPLEMENTATION.md`, control/validation reports, compatibility report, and long-run direction adjustment.

## v0.16.0 additions

- `evolution.py`: opt-in long-run diagnostics, lineage/group contingency, pair enrichment, mortality/birth pressure, and checkpointed morphology selection cohorts.
- `knowledge.py`: active root-content effective lineages, holder-root prevalence, cross-genetic-lineage/group spread, NMI and pairwise enrichment diagnostics.
- `niches.py`: shared active morphology trait schema for selection diagnostics.
- `long_run_analysis.py`: offline one/multi-run JSONL analysis with explicit observational-correlation boundary.
- `multi_seed.py`: sequential multi-seed runner with incremental index, completed-run skipping and explicit partial-output overwrite.
- `tests/test_long_run_diagnostics.py`: alignment, opt-in isolation, checkpoint restore, analyzer and runner tests.
- `configs/*_longrun.json`: 3000-tick affinity/no-affinity long-run diagnostic configurations.
- `configs/long_run_diagnostics_smoke.json`: small two-seed infrastructure validation condition.
- `LONG_RUN_DIAGNOSTICS_IMPLEMENTATION.md`, `MULTI_SEED_LONG_RUN_ANALYSIS.md`, input assessment, validation and compatibility reports.

## v0.17.0 additions

- `phase_counterfactual.py`: complete-cycle phase detection, trusted checkpoint mapping, paired multi-intervention execution and JSON/Markdown summaries.
- `interventions.py` / `simulation.py`: checkpointed `neutralize-resource-affinity`, `disable-knowledge-policy`, and `disable-knowledge-transfer` scientific interventions.
- `niches.py` / `gpu_runtime.py`: explicit effective-affinity override across policy utility, gradients, harvest assimilation and hybrid preparation.
- `long_run_analysis.py`: v2 first-difference, partial-correlation, cross-lag, trend and cross-seed sign-consistency diagnostics.
- `tests/test_phase_counterfactual.py`: intervention semantics, checkpoint persistence, phase detection and paired execution tests.
- `configs/phase_counterfactual_smoke.json`: small execution-path validation condition.
- `configs/mvp_short_latent_l2_memory_topk_inherited_heterogeneous_budget_matched_costed_transfer_longrun.json`: costed cultural-transfer long-run condition.
- `PHASE_COUNTERFACTUAL_IMPLEMENTATION.md`, `LONG_RUN_ANALYSIS_V2.md`, `THREE_SEED_LONG_RUN_ASSESSMENT.md`, validation and compatibility reports.


## v0.18.0 additions

- `knowledge.py`: explicit costed-transfer proposals/attempts/bytes/rejections, successful lineage/group transition classification, and transfer-only cultural-root diagnostics.
- `evolution.py`: checkpointed previous transfer totals and per-window transfer fields in `evolution_progress.jsonl`.
- `long_run_analysis.py`: `multi-seed-long-run-analysis-v3`, strict cultural-spread interpretability, phase-stratified transfer summaries and legacy-schema warnings.
- `phase_counterfactual.py`: disable-transfer identifiability checks based on successful pre-checkpoint commits.
- `simulation.py`: transfer trigger/probability provenance in run manifests and expanded step/cumulative metrics.
- `tests/test_knowledge.py` and `tests/test_long_run_diagnostics.py`: real successful transfer, private-root exclusion, transfer-only lineages, zero-commit interpretability and v3 analysis tests.
- `COSTED_TRANSFER_AUDIT.md`, `CULTURAL_LINEAGE_DIAGNOSTICS.md`, `LONG_RUN_ANALYSIS_V3.md`, `THREE_SEED_COSTED_TRANSFER_REASSESSMENT.md`, validation and compatibility reports.


## v0.19.0 additions

- `local_stress.py`: checkpointed observational region-window population, mortality, scarcity, hazard, crowding and benefit-flow diagnostics.
- `simulation.py` / `config.py`: opt-in local diagnostic schema, manifest provenance, birth/death/benefit hooks and exact checkpoint/clone state.
- `long_run_analysis.py`: `multi-seed-long-run-analysis-v4` spatial panel, within-region/window demeaning, first differences and local lag checks.
- `knowledge.py` / `evolution.py`: non-negative entropy denominator for small-sample NMI stability.
- `tests/test_local_stress.py`: accounting, opt-in validation, checkpoint restoration, spatial panel and small-sample NMI regression tests.
- `configs/*local_stress*.json`: long-run and short validation conditions.
- `LOCAL_SPATIAL_STRESS_DIAGNOSTICS.md`, `LONG_RUN_ANALYSIS_V4.md`, control/validation and compatibility reports.

## v0.20.0 additions

- `src/subject_evolution/local_stress.py`: opt-in `spatial-local-stress-culture-diagnostics-v2`; region-to-region transfer attempts/commits/bytes, active/effective/new/lost transferred roots, and multi-region root persistence.
- `src/subject_evolution/knowledge.py`: immutable successful-transfer commit audit and active transfer-derived holder/root presence query.
- `src/subject_evolution/simulation.py`: pure-observational regional transfer and culture-root hooks; no policy or world feedback.
- `src/subject_evolution/long_run_analysis.py`: `multi-seed-long-run-analysis-v5`, execution backend provenance, local cultural panel, observational local event studies, and cross-seed local sign consistency.
- `src/subject_evolution/local_event_counterfactual.py`: trusted-checkpoint paired interventions around region-specific scarcity, mortality, or crowding events.
- `tests/test_local_stress.py`: regional transfer-flow, root establishment/loss, and v5 panel tests.
- `tests/test_local_event_counterfactual.py`: local-event detection, prior-checkpoint mapping, identifiability and paired branch tests.
- `configs/*local_culture*.json`: v0.20 long-run and 120-tick validation configurations.
- `LOCAL_CULTURAL_TRANSFER_DIAGNOSTICS.md`, `LONG_RUN_ANALYSIS_V5.md`, `LOCAL_STRESS_EVENT_COUNTERFACTUAL.md`, control/validation and compatibility reports.


## v0.21.0 additions

- `src/subject_evolution/environment.py` / `gpu_environment.py`: opt-in local decaying/diffusing mortality trace and public danger composition.
- `src/subject_evolution/gpu_runtime.py`: mortality-trace device synchronization and deposit path.
- `src/subject_evolution/social.py`: rate-limited adaptive topology group refresh, dirty/update reason separation, predicted trust-threshold crossing and staleness bound.
- `src/subject_evolution/simulation.py`: death-location trace deposits, trace-aware signals/knowledge context, long-run trace/group audit, old checkpoint state defaults.
- `src/subject_evolution/checkpointing.py`: stored-field legacy configuration hash fallback for trusted older checkpoint bundles.
- `tests/test_mortality_trace_group_refresh.py`: trace, device parity, adaptive scheduler, checkpoint/replay, old hash and long-run audit tests.
- `configs/*mortality_trace_adaptive_groups*.json` and `v021_control_*.json`: long-run and 120-tick control conditions.
- `MORTALITY_TRACE_PERCEPTION_IMPLEMENTATION.md`, `ADAPTIVE_GROUP_REFRESH_IMPLEMENTATION.md`, control/validation and compatibility reports.

## v0.22.0 additions

- `src/subject_evolution/danger_evidence.py`: fixed-budget inherited direct-hazard versus mortality-trace evidence mixture using morphology gene 6.
- `src/subject_evolution/environment.py` / `gpu_environment.py`: deterministic toroidal moving Gaussian hazard sources and per-entity danger mixing.
- `src/subject_evolution/simulation.py` / `gpu_runtime.py`: evidence-aware danger values, gradients, signals, knowledge context, metrics, manifest and checkpoint state.
- `src/subject_evolution/interventions.py`: `neutralize-danger-evidence` scientific phenotype intervention without genotype modification.
- `src/subject_evolution/long_run_analysis.py`: `multi-seed-long-run-analysis-v6` danger evidence, mortality-trace and group-refresh endpoint audits.
- `tests/test_danger_evidence_moving_hazard.py`: fixed-budget mapping, CPU/simulated-device parity, legacy isolation, checkpoint/replay and intervention tests.
- `configs/mvp_short_v022_*.json`: 120-tick control matrix.
- `configs/*moving_hazards_evidence_longrun.json`: v0.22 long-run flagship configuration.
- `DANGER_EVIDENCE_MIXTURE_IMPLEMENTATION.md`, `MOVING_HAZARD_ENVIRONMENT_IMPLEMENTATION.md`, `LONG_RUN_ANALYSIS_V6.md`, control/validation and compatibility reports.

## v0.23.0 additions

- `src/subject_evolution/environment_process.py`: additive scalar-field process protocol, registry, entry-point discovery, config validation, metadata and v0.22 adapter resolution.
- `src/subject_evolution/plugins/moving_gaussian_hazard.py`: former in-core moving Gaussian formula as a disabled synthetic abiotic compatibility plugin.
- `tests/test_environment_process_plugins.py`: generic/legacy equivalence, device parity, custom registration, output validation and scientific-validity tests.
- `configs/mvp_short_v023_synthetic_abiotic_field_plugin_120.json`: entertainment/observation example using the generic plugin fields.
- `ENVIRONMENT_PROCESS_PLUGIN_BOUNDARY.md`, `THREE_SEED_V023_DIRECTION_ASSESSMENT.md`, `LONG_RUN_ANALYSIS_V7.md`, `MIGRATION_V023.md`, `PATCH_NOTES_V023.md` and v0.23 validation reports.
