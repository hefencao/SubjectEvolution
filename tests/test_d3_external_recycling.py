from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import numpy as np

from se.analysis.d3_conservative_intake_effects import assess_payload
from se.cfg import load_config
from se.differentiation.physiology import external_resource_recycling_enabled
from se.env.recycling import deposit_resource_residue, resource_recycling_diagnostics
from se.env.world import Environment
from se.experiments.d3_external_recycling import execute_external_recycling

ROOT=Path(__file__).resolve().parents[1]
D3C=ROOT/'configs/mvp_short_d3c_external_recycling_longrun.json'
D3B=ROOT/'configs/mvp_short_d3b_conservative_intake_longrun.json'


def test_scale_aware_d3b_assessment_accepts_rounding_residual() -> None:
    payload={
        'schema':'d3-conservative-intake-results-v1',
        'completed_seed_count':1,
        'intake_ledger':[{
            'seed':1,
            'actual_harvested':[6000.0]*4,
            'post_assimilation_overflow':[5.0e-5]*4,
            'valid':True,
        }],
        'store_ledger':[{'seed':1,'valid':True}],
    }
    report=assess_payload(payload)
    assert report['passed']
    assert report['rows'][0]['max_overflow_fraction'] < 1.0e-8


def test_v6_residue_release_preserves_channel_identity_and_mass() -> None:
    cfg=load_config(D3C)
    assert external_resource_recycling_enabled(cfg)
    env=Environment(cfg)
    env.resources.fill(0.0)
    cells=np.array([0, 1],dtype=np.int32)
    amounts=np.array([[1.0,2.0,3.0,4.0],[0.5,0.25,0.75,1.25]],dtype=np.float32)
    deposited=deposit_resource_residue(env,cells,amounts)
    before=np.asarray(resource_recycling_diagnostics(env)['resource_residue_total'])
    assert np.allclose(deposited, amounts.sum(axis=0), atol=1e-7, rtol=0.0)
    env.update(1)
    released=np.asarray(env.last_resource_residue_released,dtype=np.float64)
    after=np.asarray(resource_recycling_diagnostics(env)['resource_residue_total'])
    assert np.all(released > 0.0)
    assert np.allclose(before, released+after, atol=2e-6, rtol=0.0)
    assert np.all(env.resources.reshape(4,-1).sum(axis=1) >= released-1e-6)


def test_legacy_v5_has_no_external_residue_state() -> None:
    cfg=load_config(D3B)
    assert not external_resource_recycling_enabled(cfg)
    env=Environment(cfg)
    assert not hasattr(env,'resource_residue')


def test_d3c_end_to_end_closes_recycling_ledger(tmp_path: Path) -> None:
    cfg=load_config(D3C)
    cfg=replace(
        cfg,
        run=replace(cfg.run,ticks=20,metrics_period=5,checkpoint_period=10),
        world=replace(cfg.world,initial_entities=96,max_entities=128),
    )
    result=execute_external_recycling(
        cfg,(55001,55002),tmp_path/'run',backend='cpu',until_tick=20
    )
    assert result['completed_seed_count']==2
    assert all(row['valid'] for row in result['recycling_ledger'])
    assert result['stable_trend_summary']['store_decay_deposited_in_every_seed']
    assert result['stable_trend_summary']['external_residue_released_in_every_seed']
    assert result['recommendation']=='retain-external-recycling-and-continue-spatial-collection-processing'


def test_d3c_residue_survives_clone_and_full_checkpoint(tmp_path: Path) -> None:
    from se.runtime.sim import Simulation

    cfg=load_config(D3C)
    cfg=replace(cfg,run=replace(cfg.run,ticks=8,metrics_period=4,checkpoint_period=4,full_checkpoint_enabled=True))
    source=Simulation(cfg,tmp_path/'source',backend='cpu')
    source.run(until_tick=8)
    clone=source.clone(tmp_path/'clone')
    assert np.array_equal(clone.environment.resource_residue,source.environment.resource_residue)
    assert np.array_equal(clone.total_resource_residue_deposited,source.total_resource_residue_deposited)
    assert np.array_equal(clone.total_resource_residue_released,source.total_resource_residue_released)
    checkpoint=source.save_full_checkpoint(tmp_path/'d3c.sechk')
    restored=Simulation.from_checkpoint(checkpoint,tmp_path/'restored',backend='cpu',until_tick=8)
    assert np.array_equal(restored.environment.resource_residue,source.environment.resource_residue)
    assert np.array_equal(restored.total_resource_residue_deposited,source.total_resource_residue_deposited)
    assert np.array_equal(restored.total_resource_residue_released,source.total_resource_residue_released)
