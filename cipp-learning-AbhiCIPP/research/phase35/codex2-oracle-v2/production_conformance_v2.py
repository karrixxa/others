#!/usr/bin/env python3
"""Read-only conformance adapter for repaired Phase 35 production."""
from __future__ import annotations
from collections import deque
import hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np

HERE=Path(__file__).resolve().parent
PROD=Path('/home/cxiong/codex-runs/codex2-phase35-v2-checkout.bv1HPm/cipp-learning-AbhiCIPP')
BASE=Path('/home/cxiong/codex-runs/codex2-phase35-base-checkout/cipp-learning-AbhiCIPP')
def load_oracle():
    spec=importlib.util.spec_from_file_location('phase35_oracle_v2',HERE/'reference_oracle_v2.py')
    m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); return m
oracle=load_oracle(); sys.path.insert(0,str(PROD))
from neuron_flexible import Neuron
from snn.dendrite import CoincidencePyramidalCell
from backend.simulation import SimulationEngine,N_OUT,N_PIX

def production_case(case):
    cfg=oracle.TEST; events=[oracle.Event(**e) for e in case['events']]
    targets=sorted({e.target for e in events} or {'t0'}); cells={}
    for target in targets:
        soma=Neuron(n_inputs=1,threshold=cfg.soma_threshold,refractory_period=0,
          learning_rate=0,weight_cap=cfg.d_max,leak_rate=0); soma._weights_array=np.array([1.0])
        ws=[case.get('initial_weights',{}).get(f'{s}->{target}',cfg.d_init) for s in cfg.expected_feedback_sources]
        cells[target]=CoincidencePyramidalCell(soma,'input',list(cfg.expected_feedback_sources),
          case.get('basal_weight',cfg.basal_weight),ws,cfg.soma_threshold)
    records=[]; updates=[]; spikes=[]
    for t in sorted({e.delivered_timestep for e in events}):
        delivered=[e for e in events if e.delivered_timestep==t]
        before={target:dict(zip(cfg.expected_feedback_sources,pc.decoder_weights)) for target,pc in cells.items()}
        for e in delivered:
            if e.delivery_role!='active' or e.magnitude<=0: continue
            pc=cells[e.target]
            if e.branch=='basal':pc.deliver_basal(e.magnitude,t)
            elif e.source in cfg.expected_feedback_sources:
                pc.deliver_apical(cfg.expected_feedback_sources.index(e.source),e.magnitude,t)
        transitions=[]
        for target,pc in cells.items():
            fired=pc.resolve_coincidence(t); coincident=pc.last_coincidence_step==t
            SimulationEngine._apply_prediction_column_learning(
              SimpleNamespace(prediction_feedback_max=cfg.d_max,prediction_learning_rate=cfg.eta),pc)
            after=dict(zip(cfg.expected_feedback_sources,pc.decoder_weights))
            local=[]
            for source in cfg.expected_feedback_sources:
                if after[source]!=before[target][source]:
                    key=f'{source}->{target}'; updates.append({'timestep':t,'key':key,
                      'd_before':before[target][source],'d_after':after[source]})
                    local.append(key)
            if coincident:
                transitions.append({'target':target,'fired_using_d_before':bool(fired),'update_keys':local,
                  'basal_charge':pc.basal.charge,'apical_charge_before_learning':pc.last_d_before_learning})
            if fired: pc.fire(); spikes.append({'timestep':t,'target':target})
            pc.update()
        records.append({'timestep':t,'delivered_event_ids':sorted(e.event_id for e in delivered),
          'transitions':transitions,'weights_before':before,
          'weights_after':{target:dict(zip(cfg.expected_feedback_sources,pc.decoder_weights)) for target,pc in cells.items()},
          'end_states_clear':all(not pc.basal.deliveries and not pc.apical.deliveries for pc in cells.values())})
    return {'records':records,'updates':updates,'spikes':spikes,
      'delivery_counts':{e.event_id:1 for e in events},
      'final_weights':{f'{s}->{target}':pc.decoder_weights[n] for target,pc in cells.items()
                       for n,s in enumerate(cfg.expected_feedback_sources)}}

def projection(r,production=False):
    if production:
        ts=[x for rec in r['records'] for x in rec['transitions']]
        return {'coincidence_count':len(ts),'coincidence_targets':[x['target'] for x in ts],
          'spike_count':len(r['spikes']),'update_keys':[u['key'] for u in r['updates']],
          'delivery_counts':r['delivery_counts'],'end_states_clear':all(rec['end_states_clear'] for rec in r['records'])}
    s=oracle.summary(r); return {k:s[k] for k in ('coincidence_count','coincidence_targets','spike_count','update_keys','delivery_counts','end_states_clear')}

def queue_regression():
    eng=SimulationEngine(seed=1,prediction_column_enabled=True,prediction_feedback_init=400,
      prediction_lateral_weight=150,prediction_threshold=500,prediction_learning_rate=0,refractory=0)
    ap=np.zeros(N_OUT);ap[0]=1;ba=np.zeros(N_PIX);ba[4]=1
    eng.l2e_to_pcol_queue=deque([ap]);eng.s_to_pcol_queue=deque([ba])
    eng.pcol_delivery_metadata_queue=deque([[
      {'source':'L2E0','target':'PC4','target_compartment':'apical','scheduled_step':-1,'arrival_step':0,'origin_pattern':'row 1'},
      {'source':'L1E4','target':'PC4','target_compartment':'basal','scheduled_step':-1,'arrival_step':0,'origin_pattern':'row 1'}]])
    before={'apical':eng.l2e_to_pcol_queue[0].tolist(),'basal':eng.s_to_pcol_queue[0].tolist()}
    eng.set_pattern('col 1'); preserved=(before['apical']==eng.l2e_to_pcol_queue[0].tolist() and before['basal']==eng.s_to_pcol_queue[0].tolist())
    eng.input_vec[:]=0; eng.step(); first_spike=bool(eng.spiked['PC4'])
    delivered=eng.dynamic_state()['prediction_column']['last_deliveries']; eng.step()
    return {'preserved_across_switch':preserved,'first_delivery_spike':first_spike,
      'delivered_count':len(delivered),'delivery_sources':sorted(x['source'] for x in delivered),
      'origin_classes':sorted({x['origin_class'] for x in delivered}),
      'second_step_spike':bool(eng.spiked['PC4']),
      'second_step_last_deliveries':eng.dynamic_state()['prediction_column']['last_deliveries'],
      'passes':preserved and first_spike and len(delivered)==2 and not eng.spiked['PC4']}

def default_snapshot(root):
    code='''import json,sys,hashlib;sys.path.insert(0,sys.argv[1]);from backend.simulation import SimulationEngine;e=SimulationEngine(seed=7);rows=[]\nfor _ in range(5):\n e.step();rows.append({"t":e.timestep,"spiked":sorted((k,bool(v)) for k,v in e.spiked.items()),"weights":e._all_weights()})\nprint(hashlib.sha256(json.dumps(rows,sort_keys=True,default=lambda x:x.tolist() if hasattr(x,"tolist") else x).encode()).hexdigest())'''
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    return subprocess.check_output([sys.executable,'-c',code,str(root)],text=True,env=env).strip()

def main():
    gold=json.loads((HERE/'golden_cases_v2.json').read_text())['cases']; comparisons=[]; traces=[]
    for case in gold:
        es=[oracle.Event(**e) for e in case['events']]
        o=oracle.simulate(es,oracle.TEST,case.get('initial_weights'),case.get('basal_weight'))
        p=production_case(case); op=projection(o);pp=projection(p,True);match=op==pp
        comparisons.append({'name':case['name'],'match':match,'oracle':op,'production':pp})
        if not match:traces.append({'test':case['name'],'first_divergence':{'oracle':op,'production':pp},
          'oracle_records':o['records'],'production_records':p['records']})
    queue=queue_regression(); base=default_snapshot(BASE); repaired=default_snapshot(PROD)
    sparse=next(x for x in comparisons if x['name']=='three_active_targets_of_nine')
    sparse_case=next(x for x in gold if x['name']=='three_active_targets_of_nine')
    sparse_full=production_case(sparse_case)
    sparse_changed=sorted(u['key'] for u in sparse_full['updates'])
    sparse_unchanged=sorted(k for k,v in sparse_full['final_weights'].items()
      if k.startswith('feedback->') and float(v).hex()==float(oracle.TEST.d_init).hex())
    maturity=next(x for x in comparisons if x['name']=='decoder_threshold_crossing')
    gating_disagreement=[]
    if any(x['name'] in {'basal_only','apical_only_max_weight','same_step_coincidence'} and not x['match'] for x in comparisons):
        gating_disagreement.append('direct gate projection differs')
    if not queue['passes']: verdict='QUEUE_REPAIR_MISMATCH'
    elif base!=repaired: verdict='DEFAULT_OFF_MISMATCH'
    elif gating_disagreement: verdict='GATING_CONTRACT_MISMATCH'
    elif any(not x['match'] for x in comparisons): verdict='LEARNING_EQUATION_MISMATCH'
    else: verdict='REPAIRED_PRODUCTION_CONFORMS_TO_ORACLE_V2'
    result={'verdict':verdict,'production_commit':'db30ceadbe18cf90e01f6d54dee0203f342b24a8',
      'goldens':{'count':len(comparisons),'matches':sum(x['match'] for x in comparisons),'comparisons':comparisons},
      'queue_regression':queue,'maturity_case':maturity,
      'three_of_nine':{'comparison':sparse,'changed':sparse_changed,
        'unchanged_byte_identical':sparse_unchanged},
      'gating_contract_disagreement':gating_disagreement,
      'default_off':{'base_hash':base,'repaired_hash':repaired,'match':base==repaired}}
    existing=json.loads((HERE/'results.json').read_text())
    oracle_results=existing['oracle'] if 'oracle' in existing else existing
    (HERE/'results.json').write_text(json.dumps({'oracle':oracle_results,
      'production_conformance':result},indent=2,sort_keys=True)+'\n')
    (HERE/'mismatch_traces_v2.json').write_text(json.dumps({'count':len(traces),'traces':traces},indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'matches':result['goldens']['matches'],'goldens':len(comparisons),
      'queue':queue['passes'],'default_off':base==repaired,'mismatches':len(traces)}))
if __name__=='__main__':main()
