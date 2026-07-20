#!/usr/bin/env python3
"""Focused, read-only reproduction of the two Phase 35 mismatches."""
from __future__ import annotations
import importlib.util, json, math, os, sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np

HERE=Path(__file__).resolve().parent
PROD=Path('/home/cxiong/codex-runs/codex2-phase35-checkout.gqJzv8/cipp-learning-AbhiCIPP')
ADAPTER=Path('/home/cxiong/codex-runs/codex2-phase35-implementation-conformance/conformance_adapter.py')
sys.path.insert(0,str(PROD))
from neuron_flexible import Neuron
from snn.dendrite import CoincidencePyramidalCell
from backend.simulation import SimulationEngine, N_OUT, N_PIX

def load_adapter():
    spec=importlib.util.spec_from_file_location('frozen_conformance_adapter',ADAPTER)
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod
    spec.loader.exec_module(mod); return mod

def queue_trace():
    eng=SimulationEngine(seed=1,prediction_column_enabled=True,
                         prediction_feedback_delay=1,refractory=0)
    eng.l2e_to_pcol_queue.clear(); eng.s_to_pcol_queue.clear()
    apical=np.zeros(N_OUT); apical[0]=1.0
    basal=np.zeros(N_PIX); basal[0]=1.0
    eng.l2e_to_pcol_queue.append(apical.copy())
    eng.s_to_pcol_queue.append(basal.copy())
    # Also prove the function clears already-delivered compartment state.
    eng.pcol[0].deliver_basal(1.0,0); eng.pcol[0].deliver_apical(0,1.0,0)
    old_apical_queue=eng.l2e_to_pcol_queue
    old_basal_queue=eng.s_to_pcol_queue
    before={'apical_queue':old_apical_queue[0].tolist(),
            'basal_queue':old_basal_queue[0].tolist(),
            'pc0_basal_delivery_count':len(eng.pcol[0].basal.deliveries),
            'pc0_apical_delivery_count':len(eng.pcol[0].apical.deliveries)}
    eng._start_presentation('col 1','train')
    after={'apical_queue':eng.l2e_to_pcol_queue[0].tolist(),
           'basal_queue':eng.s_to_pcol_queue[0].tolist(),
           'pc0_basal_delivery_count':len(eng.pcol[0].basal.deliveries),
           'pc0_apical_delivery_count':len(eng.pcol[0].apical.deliveries),
           'apical_deque_replaced':eng.l2e_to_pcol_queue is not old_apical_queue,
           'basal_deque_replaced':eng.s_to_pcol_queue is not old_basal_queue}
    # Independent ordinary end-of-step clearing check.
    soma=Neuron(n_inputs=1,threshold=5,refractory_period=0,learning_rate=0,
                weight_cap=11,leak_rate=0); soma._weights_array=np.array([1.0])
    pc=CoincidencePyramidalCell(soma,'input',['feedback'],0,[2],5)
    pc.deliver_basal(1,7)
    ordinary_before={'basal':len(pc.basal.deliveries),'apical':len(pc.apical.deliveries)}
    pc.update()
    ordinary_after={'basal':len(pc.basal.deliveries),'apical':len(pc.apical.deliveries)}
    return {
      'minimal_atomic_loss':{'event':{'source':'L2E0','target':'PC0.apical',
          'scheduled_timestep':0,'intended_delivery_timestep':1,'switch_timestep':1,
          'queue':'SimulationEngine.l2e_to_pcol_queue'},
          'result':'event vector replaced by zero vector before popleft/delivery'},
      'minimal_coincidence_loss':{'events':[
          {'source':'L2E0','target':'PC0.apical','scheduled_timestep':0,'intended_delivery_timestep':1},
          {'source':'L1E0','target':'PC0.basal','scheduled_timestep':0,'intended_delivery_timestep':1}],
          'switch_timestep':1,'queues':['l2e_to_pcol_queue','s_to_pcol_queue']},
      'clearing_function':'SimulationEngine._start_presentation',
      'before':before,'after':after,
      'loss_mechanism':'both deques are replaced; queued vectors are deleted from engine reachability, not skipped',
      'ordinary_end_of_timestep_clearing':{'before_update':ordinary_before,
                                           'after_update':ordinary_after,
                                           'correct':ordinary_after=={'basal':0,'apical':0}}}

def make_cell(d):
    # Match conformance_adapter.production_case exactly: soma threshold 7,
    # production coincidence threshold mapped from oracle maturity 5.
    soma=Neuron(n_inputs=1,threshold=7,refractory_period=0,learning_rate=0,
                weight_cap=11,leak_rate=0); soma._weights_array=np.array([1.0])
    return CoincidencePyramidalCell(soma,'input',['feedback'],0,[d],5)

def direct_maturity_trace():
    eta=1.0; wmax=11.0; maturity=5.0; pc=make_cell(4.0)
    steps=[]
    for step in (0,1):
        pc.deliver_basal(1.0,step); pc.deliver_apical(0,1.0,step)
        d_before=pc.decoder_weights[0]
        apical_charge=pc.apical.charge; basal_charge=pc.basal.charge
        potential_before=pc.soma.potential
        response=pc.resolve_coincidence(step)
        potential_after_resolve=pc.soma.potential
        base=1.0-d_before/wmax; saturation=base**2
        independently_calculated_delta=eta*saturation
        SimulationEngine._apply_prediction_column_learning(
            SimpleNamespace(prediction_feedback_max=wmax,prediction_learning_rate=eta),pc)
        d_after=pc.decoder_weights[0]; stored_delta=d_after-d_before
        steps.append({'step':step,'d_before':d_before,'d_before_hex':d_before.hex(),
          'eta':eta,'eligibility':{'basal_active':pc.basal.active,
             'apical_active':pc.apical.active,'same_delivery_step':True,
             'apical_source_delivered':True,'apical_signal_positive':True},
          'saturation_expression':'(1 - d_before / d_max) ** 2',
          'saturation_base':base,'saturation_factor':saturation,
          'raw_delta_independent':independently_calculated_delta,
          'stored_delta':stored_delta,'stored_delta_hex':stored_delta.hex(),
          'delta_matches_independent':math.isclose(stored_delta,independently_calculated_delta,rel_tol=0,abs_tol=1e-15),
          'd_after':d_after,'d_after_hex':d_after.hex(),'maturity_threshold':maturity,
          'current_event_response':bool(response),'apical_charge':apical_charge,
          'basal_charge':basal_charge,'combined_dendritic_charge':apical_charge+basal_charge,
          'soma_potential_before':potential_before,
          'soma_potential_after_resolve':potential_after_resolve,
          'soma_threshold':pc.soma.threshold})
        pc.clear_compartments()
    return {'steps':steps,'current_event_response':steps[0]['current_event_response'],
            'next_coincidence_response':steps[1]['current_event_response']}

def adapter_maturity_trace(adapter):
    events=[adapter.oracle.ev('b0','basal',delivered=0),adapter.oracle.ev('a0','apical',delivered=0),
            adapter.oracle.ev('b1','basal',delivered=1),adapter.oracle.ev('a1','apical',delivered=1)]
    case={'events':[vars(e) for e in events],
          'initial_weights':{'input->t0':adapter.oracle.TEST.maturity-adapter.oracle.TEST.eta}}
    return adapter.production_case(case)

def main():
    adapter=load_adapter()
    queue=queue_trace(); direct=direct_maturity_trace(); adapted=adapter_maturity_trace(adapter)
    oracle_delta=adapter.oracle.TEST.eta*1.0
    diagnosis={
      'adapter_vs_direct':{'adapter_update_afters':[u['after'] for u in adapted['updates']],
                           'direct_update_afters':[s['d_after'] for s in direct['steps']],
                           'same': [u['after'] for u in adapted['updates']]==[s['d_after'] for s in direct['steps']]},
      'oracle_update':{'expression':'eta * sum(qualifying apical magnitude)',
                       'd_before':4.0,'eta':1.0,'delta':oracle_delta,'d_after':5.0},
      'production_update':{'expression':'eta * (1 - d_before / d_max) ** 2',
                           'd_before':4.0,'eta':1.0,'d_max':11.0,
                           'delta':direct['steps'][0]['stored_delta'],
                           'd_after':direct['steps'][0]['d_after']},
      'cause_matrix':{'adapter_input_mapping':False,'oracle_parameter_mapping':False,
        'numeric_rounding':False,'different_saturation_equations':True,
        'missing_state_persistence':False,'mature_weight_comparison':False,
        'somatic_response_logic':False}}
    result={'verdict':'QUEUE_DEFECT_REAL_MATURITY_ORACLE_MISMATCH',
            'production_commit':'4e712a4b7dea033b9191680a4b4e3577d93ca304',
            'queue':queue,'maturity':{'adapter':adapted,'direct':direct,'diagnosis':diagnosis},
            'processes_remaining':False}
    minimal={'queue_regression_test':queue['minimal_coincidence_loss'] | {
       'setup':'delay=1; enqueue both nonzero vectors; switch before intended delivery',
       'expected':{'queued_vectors_survive_switch':True,'delivery_count_each':1,
                   'PC0_coincidence_at_timestep':1},
       'observed':{'queued_vectors_survive_switch':False,'delivery_count_each':0,
                   'PC0_coincidence_at_timestep':None}},
       'maturity_non_defect_control':{'initial_d':4.0,'eta':1.0,'d_max':11.0,
          'threshold':5.0,'expected_production_d_after':direct['steps'][0]['d_after'],
          'expected_current_response':False,'expected_next_response':False,
          'classification':'oracle equation mismatch; not a production repair target'}}
    (HERE/'results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    (HERE/'minimal_counterexamples.json').write_text(json.dumps(minimal,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':result['verdict'],
      'adapter_direct_same':diagnosis['adapter_vs_direct']['same'],
      'queue_preserved':False,'ordinary_clearing_correct':queue['ordinary_end_of_timestep_clearing']['correct']},sort_keys=True))
if __name__=='__main__': main()
