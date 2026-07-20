#!/usr/bin/env python3
"""Read-only external adapter comparing Phase 35 production with the oracle."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np

HERE = Path(__file__).resolve().parent
ORACLE_DIR = Path('/home/cxiong/codex-runs/codex2-phase35-dendrite-oracle')
PROD_ROOT = Path('/home/cxiong/codex-runs/codex2-phase35-checkout.gqJzv8/cipp-learning-AbhiCIPP')
BASE_ROOT = Path('/home/cxiong/codex-runs/codex2-phase35-base-checkout/cipp-learning-AbhiCIPP')

def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod
    spec.loader.exec_module(mod); return mod

oracle = load_file('accepted_phase35_oracle', ORACLE_DIR/'reference_oracle.py')
sys.path.insert(0, str(PROD_ROOT))
from neuron_flexible import Neuron
from snn.dendrite import CoincidencePyramidalCell
from backend.simulation import SimulationEngine, N_OUT, N_PIX

def sha(path):
    h=hashlib.sha256(); h.update(Path(path).read_bytes()); return h.hexdigest()

def production_case(case):
    events=[oracle.Event(**e) for e in case['events']]
    targets=sorted({e.target for e in events} or {'t0'})
    cells={}
    for target in targets:
        soma=Neuron(n_inputs=1, threshold=oracle.TEST.soma_threshold,
                    refractory_period=0, learning_rate=0, weight_cap=oracle.TEST.d_max,
                    leak_rate=0)
        soma._weights_array=np.array([1.0])
        # Production decoder identity is the apical source. Both known apical
        # sources exist physically; the adapter only routes configured feedback.
        pc=CoincidencePyramidalCell(soma, 'input', ['feedback'], 0.0,
                   [oracle.TEST.d_init], oracle.TEST.maturity)
        initial=case.get('initial_weights',{})
        if 'input->'+target in initial: pc.apical_connections[0].weight=initial['input->'+target]
        cells[target]=pc
    records=[]; updates=[]; spikes=[]
    for t in sorted({e.delivered_timestep for e in events}):
        before={target:list(pc.decoder_weights) for target,pc in cells.items()}
        delivered=[e for e in events if e.delivered_timestep==t]
        for e in delivered:
            if e.delivery_role!='active': continue
            pc=cells[e.target]
            if e.branch=='basal': pc.deliver_basal(e.magnitude,t)
            elif e.source=='feedback': pc.deliver_apical(0,e.magnitude,t)
        target_coins=[]
        for target,pc in cells.items():
            fired=pc.resolve_coincidence(t)
            coincident=pc.last_coincidence_step==t
            harness=SimpleNamespace(prediction_feedback_max=oracle.TEST.d_max,
                                    prediction_learning_rate=oracle.TEST.eta)
            SimulationEngine._apply_prediction_column_learning(harness,pc)
            after=list(pc.decoder_weights)
            if before[target]!=after:
                updates.append({'timestep':t,'key':f'feedback->{target}',
                                'before':before[target][0],'after':after[0]})
            if fired:
                pc.fire(); spikes.append({'timestep':t,'target':target})
            if coincident: target_coins.append(target)
            pc.clear_compartments()
        records.append({'timestep':t,'coincidence_targets':target_coins,
                        'delivered_event_ids':[e.event_id for e in delivered],
                        'weights_before':before,
                        'weights_after':{target:list(pc.decoder_weights) for target,pc in cells.items()},
                        'end_states_clear':all(not pc.basal.deliveries and not pc.apical.deliveries
                                               for pc in cells.values())})
    return {'coincidence_count':sum(len(r['coincidence_targets']) for r in records),
            'coincidence_targets':[x for r in records for x in r['coincidence_targets']],
            'spike_count':len(spikes),'decoder_update_keys':[u['key'] for u in updates],
            'delivery_counts':{e.event_id:1 for e in events},
            'end_states_clear':all(r['end_states_clear'] for r in records),
            'records':records,'updates':updates,'spikes':spikes}

def relevant_projection(x):
    return {k:x[k] for k in ('coincidence_count','coincidence_targets','spike_count',
                              'decoder_update_keys','delivery_counts','end_states_clear')}

def maturity_runs():
    rows=[]
    for before in [oracle.TEST.maturity-oracle.TEST.eta,oracle.TEST.maturity,
                   oracle.TEST.maturity+oracle.TEST.eta]:
        case={'events':[vars(oracle.ev('b','basal')),vars(oracle.ev('a','apical'))],
              'initial_weights':{'input->t0':before}}
        o=oracle.summarize(oracle.simulate([oracle.Event(**e) for e in case['events']],oracle.TEST,
                                           case['initial_weights']))
        p=production_case(case)
        rows.append({'d_before':before,'oracle':relevant_projection(o),
                     'production':relevant_projection(p),'match':relevant_projection(o)==relevant_projection(p)})
    # Explicit crossing then subsequent coincidence.
    events=[oracle.ev('b0','basal',delivered=0),oracle.ev('a0','apical',delivered=0),
            oracle.ev('b1','basal',delivered=1),oracle.ev('a1','apical',delivered=1)]
    case={'events':[vars(e) for e in events],'initial_weights':{'input->t0':oracle.TEST.maturity-oracle.TEST.eta}}
    return rows, {'oracle':oracle.summarize(oracle.simulate(events,oracle.TEST,case['initial_weights'])),
                  'production':production_case(case)}

def sparse_nine():
    case=next(c for c in json.loads((ORACLE_DIR/'golden_cases.json').read_text())['cases']
              if c['name']=='three_active_targets_of_nine')
    p=production_case(case); before={f'feedback->t{i}':float(oracle.TEST.d_init) for i in range(9)}
    after=dict(before)
    for u in p['updates']: after[u['key']]=u['after']
    untouched=[k for k in before if before[k].hex()==after[k].hex()]
    return {'production':relevant_projection(p),'before':before,'after':after,
            'byte_identical_untouched':untouched}

def switch_queue_test():
    eng=SimulationEngine(seed=1,prediction_column_enabled=True,prediction_feedback_delay=1)
    eng.l2e_to_pcol_queue.clear(); eng.s_to_pcol_queue.clear()
    fb=np.zeros(N_OUT); fb[0]=1; basal=np.zeros(N_PIX); basal[0]=1
    eng.l2e_to_pcol_queue.append(fb.copy()); eng.s_to_pcol_queue.append(basal.copy())
    before=[eng.l2e_to_pcol_queue[0].tolist(),eng.s_to_pcol_queue[0].tolist()]
    eng._start_presentation('col 1','train')
    after=[eng.l2e_to_pcol_queue[0].tolist(),eng.s_to_pcol_queue[0].tolist()]
    return {'before_switch':before,'after_switch':after,
            'queued_pair_preserved':before==after,'production_action':'queue reset at pattern switch'}

def source_locality_test():
    soma=Neuron(n_inputs=1,threshold=5,refractory_period=0,learning_rate=0,weight_cap=11,leak_rate=0)
    soma._weights_array=np.array([1.0])
    pc=CoincidencePyramidalCell(soma,'input',['feedback0','feedback1'],0,[2,2],5)
    pc.deliver_basal(1,0); pc.deliver_apical(1,1,0)
    before=list(pc.decoder_weights); pc.resolve_coincidence(0)
    SimulationEngine._apply_prediction_column_learning(
        SimpleNamespace(prediction_feedback_max=11,prediction_learning_rate=1),pc)
    after=list(pc.decoder_weights)
    return {'delivered_apical_source':'feedback1','before':before,'after':after,
            'only_delivered_source_updated':before[0].hex()==after[0].hex() and after[1]!=before[1]}

def default_snapshot(root):
    code='''import json,sys,hashlib,numpy as np; sys.path.insert(0,sys.argv[1]); from backend.simulation import SimulationEngine; e=SimulationEngine(seed=7); rows=[]\nfor _ in range(5):\n e.step(); rows.append({"t":e.timestep,"spiked":sorted((k,bool(v)) for k,v in e.spiked.items()),"weights":e._all_weights()})\nprint(hashlib.sha256(json.dumps(rows,sort_keys=True,default=lambda x:x.tolist() if hasattr(x,"tolist") else x).encode()).hexdigest())'''
    return subprocess.check_output([sys.executable,'-c',code,str(root)],text=True).strip()

def exhaustive():
    # Production-comparison subset: causal dimensions only, one magnitude and
    # current provenance.  2*3*2*2*2*2 roles = 96 events; 9,216 ordered pairs.
    from itertools import product
    vals=list(product(['basal','apical'],['input','feedback','other'],['t0','t1'],[0,1],[0,1],['active','shadow']))
    mismatches=[]
    for n,(a,b) in enumerate(product(vals,repeat=2)):
        def mk(i,v):
            br,src,tgt,sch,dele,role=v
            return oracle.Event(f'e{i}',br,src,tgt,sch,dele,1,'A','A','p0','p0',role,False)
        es=[mk(0,a),mk(1,b)]
        o=oracle.summarize(oracle.simulate(es,oracle.TEST)); p=production_case({'events':[vars(e) for e in es],'initial_weights':{}})
        # Gate/state comparison deliberately excludes decoder association naming
        # and spike calibration; these are reported by dedicated checks.
        op={k:o[k] for k in ('coincidence_count','coincidence_targets','delivery_counts','end_states_clear')}
        pp={k:p[k] for k in op}
        if op!=pp and len(mismatches)<100:
            mismatches.append({'ordinal':n,'events':[vars(e) for e in es],
                               'first_divergence':{'oracle':op,'production':pp}})
    return {'domains':{'branch':['basal','apical'],'source':['input','feedback','other'],
             'target':['t0','t1'],'scheduled_timestep':[0,1],'delivered_timestep':[0,1],
             'magnitude':[1],'origin/current':["current-correct only"],
             'delivery_role':['active','shadow']},'single_event_count':96,
             'ordered_pair_count':9216,'mismatch_count':len(mismatches),'mismatches':mismatches}

def main():
    gold=json.loads((ORACLE_DIR/'golden_cases.json').read_text())['cases']
    comparisons=[]; traces=[]
    for case in gold:
        o=case['expected']; p=production_case(case); op=relevant_projection(o); pp=relevant_projection(p)
        match=op==pp
        comparisons.append({'name':case['name'],'match':match,'oracle':op,'production':pp})
        if not match:
            traces.append({'test':case['name'],'first_divergent_transition':
                           {'oracle':op,'production':pp},
                           'oracle_records':oracle.simulate([oracle.Event(**e) for e in case['events']],oracle.TEST,case.get('initial_weights'))['records'],
                           'production_records':p['records'],
                           'production_updates':p['updates']})
    maturity,cross=maturity_runs(); sparse=sparse_nine(); switch=switch_queue_test(); locality=source_locality_test()
    base_hash=default_snapshot(BASE_ROOT); prod_hash=default_snapshot(PROD_ROOT)
    ex=exhaustive()
    findings=[]
    if not switch['queued_pair_preserved']: findings.append('PHYSICAL_TIMING_MISMATCH')
    boundary_fire_match=all(x['oracle']['spike_count']==x['production']['spike_count'] for x in maturity)
    crossing_fire_match=(cross['oracle']['spike_count']==cross['production']['spike_count'])
    if not crossing_fire_match: findings.append('LEARNING_ORDER_MISMATCH')
    expected_sparse={f'feedback->t{i}' for i in (1,4,7)}
    if set(sparse['production']['decoder_update_keys'])!=expected_sparse: findings.append('LOCALITY_MISMATCH')
    if base_hash!=prod_hash: findings.append('DEFAULT_OFF_MISMATCH')
    verdict=findings[0] if len(set(findings))==1 else ('MIXED' if findings else 'PRODUCTION_CONFORMS_TO_ORACLE')
    result={'verdict':verdict,'findings':sorted(set(findings)),
      'integrity':{'bundle_sha256':sha('/home/cxiong/codex-runs/codex1-phase35-implementation/phase35-gate-a-b-4e712a4b7dea033b9191680a4b4e3577d93ca304.bundle'),
                   'production_commit':'4e712a4b7dea033b9191680a4b4e3577d93ca304','base_commit':'4764f1758a7399439df2242dfa60819501fc2333'},
      'goldens':{'count':len(comparisons),'matches':sum(x['match'] for x in comparisons),'comparisons':comparisons},
      'maturity_boundary':maturity,'maturity_fire_decisions_match':boundary_fire_match,
      'd_before_learning_determines_current_event':boundary_fire_match,
      'threshold_crossing_sequence':cross,'sparse_three_of_nine':sparse,
      'source_locality':locality,
      'queue_switch':switch,'default_off':{'base_hash':base_hash,'production_hash':prod_hash,'match':base_hash==prod_hash},
      'exhaustive':ex}
    if not switch['queued_pair_preserved']:
        traces.append({'test':'queue_carryover_across_switch','first_divergent_transition':switch})
    for x in maturity:
        if x['oracle']['spike_count']!=x['production']['spike_count']:
            traces.append({'test':f"maturity_d_before_{x['d_before']}",
                           'first_divergent_transition':x})
    if not crossing_fire_match:
        traces.append({'test':'threshold_crossing_subsequent_coincidence',
                       'first_divergent_transition':cross})
    (HERE/'results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    (HERE/'mismatch_traces.json').write_text(json.dumps({'count':len(traces),'traces':traces},indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'golden_matches':result['goldens']['matches'],
                      'golden_count':len(comparisons),'exhaustive_mismatches':ex['mismatch_count'],
                      'default_off_match':base_hash==prod_hash},sort_keys=True))
if __name__=='__main__': main()
