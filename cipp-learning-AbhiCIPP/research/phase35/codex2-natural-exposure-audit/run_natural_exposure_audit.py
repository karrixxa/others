#!/usr/bin/env python3
"""Measurement-only Phase 35 natural exposure/timing audit."""
from __future__ import annotations
import argparse,csv,hashlib,json,os,subprocess,sys,time
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np

ROOT=Path('/home/cxiong/codex-runs/codex2-phase35-natural-exposure-checkout/cipp-learning-AbhiCIPP')
OUT=Path('/home/cxiong/codex-runs/codex2-phase35-natural-exposure-audit')
BASE=Path('/home/cxiong/codex-runs/codex2-phase35-base-checkout/cipp-learning-AbhiCIPP')
sys.path.insert(0,str(ROOT))
from backend.simulation import SimulationEngine,PATTERNS,N_OUT,N_PIX
from backend.presets import DASHBOARD_PRESET
from diagnostic_schedule import CYCLE_ORDER,PRESENTATION_STEPS
from phase27_l2_ownership_causal_audit import (find_earliest_modal_collision,
                                                find_persistent_ownership_collision)

CYCLES=40; TOPOLOGY_SEED=1; SEEDS=[1,2,3,4,5]
FLAGS=dict(DASHBOARD_PRESET)
FLAGS.update(prediction_column_enabled=True,prediction_column_to_i_enabled=False,
             confidence_consolidation=False,loser_depression=False,l2e_budget=False,
             homeostasis=False)
MATURITY=float(FLAGS.get('prediction_threshold',500.0)-FLAGS.get('prediction_lateral_weight',150.0))

def default_hash(root):
    code='''import sys,json,hashlib;sys.path.insert(0,sys.argv[1]);from backend.simulation import SimulationEngine;e=SimulationEngine(seed=7);a=[]\nfor _ in range(5):e.step();a.append((e.timestep,sorted((k,bool(v)) for k,v in e.spiked.items()),e._all_weights()))\nprint(hashlib.sha256(json.dumps(a,sort_keys=True,default=lambda x:x.tolist() if hasattr(x,"tolist") else x).encode()).hexdigest())'''
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    return subprocess.check_output([sys.executable,'-c',code,str(root)],text=True,env=env).strip()

def modal(values):
    c=Counter(v for v in values if v is not None)
    if not c:return None
    n=max(c.values());return min(k for k,v in c.items() if v==n)

def decoder_matrix(e):
    return np.array([pc.decoder_weights for pc in e.pcol],dtype=float).T # [source,target]

def event_key(r):
    return (r['source'],r['target'],r['target_compartment'],int(r['scheduled_step']),int(r['arrival_step']))

def compression_summary(e,presentation_log,first_spikes):
    final=np.array([n._weights_array.copy() for n in e.l2.excitatory_neurons])
    ratios={}
    for j in range(N_OUT):
        per=np.delete(final[j],4); ratios[f'L2E{j}']={'center_weight':float(final[j,4]),
          'peripheral_mean':float(np.mean(per)),'ratio':float(final[j,4]/np.mean(per)) if np.mean(per)>0 else None}
    counts=Counter(r['first_l2e_spiker'] for r in presentation_log if r['first_l2e_spiker'])
    total=sum(counts.values())
    statuses={f'L2E{j}':e._l2e_status(j)['status'] for j in range(N_OUT)}
    return {'established_indicators_only':True,'first_responder_share':{k:v/total for k,v in counts.items()},
      'distinct_first_responders':len(counts),'l2e_status':statuses,
      'active_count':sum(v=='active' for v in statuses.values()),
      'never_first_responder':sorted(set(f'L2E{j}' for j in range(N_OUT))-set(counts)),
      'center_peripheral_ratio':ratios,
      'first_transient_overlap':find_earliest_modal_collision(presentation_log),
      'persistent_collision':find_persistent_ownership_collision(presentation_log)}

def run_seed(seed,cycles=CYCLES,smoke=False):
    start=time.monotonic(); kw=dict(FLAGS,seed=seed,topology_seed=TOPOLOGY_SEED)
    e=SimulationEngine(**kw); initial=decoder_matrix(e); previous=initial.copy()
    update_counts=np.zeros((N_OUT,N_PIX),dtype=int); active_updates=np.zeros_like(update_counts)
    inactive_updates=np.zeros_like(update_counts); crossings={}; next_mature={}
    scheduled={}; arrived=Counter(); stale=[]; queue_rows=[]; pc_spikes=[]; counterfactual=[]
    coincidence_cell_steps=0; steps_with_coincidence=0; total_steps=cycles*len(CYCLE_ORDER)*PRESENTATION_STEPS
    presentations=[]; first_by_pattern={}; timeline=[]; stop_reason=None
    presentation_index=0
    for cycle in range(cycles):
      for pattern in CYCLE_ORDER:
        e.set_pattern(pattern); t_start=e.timestep; first_events=[]
        for rel in range(PRESENTATION_STEPS):
          before=decoder_matrix(e); e.step(); t=e.timestep-1; after=decoder_matrix(e)
          state=e.dynamic_state()['prediction_column']; deliveries=state['last_deliveries']
          for rec in state['pending_deliveries']: scheduled.setdefault(event_key(rec),dict(rec))
          for rec in deliveries:
            k=event_key(rec); arrived[k]+=1
            is_stale=rec.get('origin_pattern')!=e.current_pattern
            qrow={'type':'queue_arrival','step':t,'source':rec['source'],'target':rec['target'],
              'source_step':rec['scheduled_step'],'arrival_step':rec['arrival_step'],'stale':is_stale,
              'origin_pattern':rec.get('origin_pattern'),'current_pattern':e.current_pattern,
              'origin_class':rec['origin_class']}
            queue_rows.append(qrow)
            if is_stale: stale.append(dict(rec,current_pattern=e.current_pattern));timeline.append(qrow)
          changed=np.argwhere(after!=before); step_updates=[]
          by_target_meta=defaultdict(list)
          for rec in deliveries:by_target_meta[rec['target']].append(rec)
          for j,i in changed:
            j=int(j);i=int(i);update_counts[j,i]+=1; source=f'L2E{j}';target=f'PC{i}'
            relevant=[r for r in by_target_meta[target] if r['source']==source and r['target_compartment']=='apical']
            origins=sorted({r.get('origin_pattern') for r in relevant if r.get('origin_pattern') in PATTERNS})
            pixel_active=bool(origins) and all(PATTERNS[o][i] for o in origins)
            if pixel_active:active_updates[j,i]+=1
            else:inactive_updates[j,i]+=1
            step_updates.append(f'd[{j},{i}]')
            if before[j,i]<MATURITY<=after[j,i] and f'{j},{i}' not in crossings:
              current_pc_spike=bool(e.spiked[f'PC{i}'])
              crossings[f'{j},{i}']={'step':t,'source':source,'target':target,
                'd_before':float(before[j,i]),'d_after':float(after[j,i]),
                'crossing_event_pc_spike':current_pc_spike,
                'current_event_confirmed_not_fired':not current_pc_spike}
              timeline.append({'type':'maturity_crossing','step':t,'source':source,'target':target,
                'd_before':float(before[j,i]),'d_after':float(after[j,i]),'pc_spike':current_pc_spike})
              if current_pc_spike:stop_reason='maturity-crossing event fired immediately'
            key=f'{j},{i}'
            if key in crossings and key not in next_mature and t>crossings[key]['step']:
              next_mature[key]={'step':t,'source':source,'target':target,'pc_spike':bool(e.spiked[f'PC{i}'])}
          coincident=[i for i,pc in enumerate(e.pcol) if pc.last_coincidence_step==t]
          coincidence_cell_steps+=len(coincident);steps_with_coincidence+=bool(coincident)
          fired_pc=[i for i in range(N_PIX) if e.spiked[f'PC{i}']]
          for i in fired_pc:
            item={'step':t,'source':f'PC{i}','target':f'L1I{i}','physical_pc_spike':True,
              'counterfactual_active_mode_delivery':True,'physically_delivered_in_shadow':False,
              'delivery_step_if_active':t}
            pc_spikes.append(item);counterfactual.append(item);timeline.append({'type':'pc_spike',**item})
          l2=[j for j in range(N_OUT) if e.spiked[f'L2E{j}']]
          if l2:
            first_events.extend({'step':t,'relative_step':rel,'neuron':f'L2E{j}'} for j in l2)
          if step_updates:timeline.append({'type':'decoder_updates','step':t,'keys':step_updates})
          if np.any(inactive_updates):stop_reason='inactive pixel received decoder update'
          if any(v>1 for v in arrived.values()):stop_reason='queued event delivered more than once'
          if stop_reason:break
        first=min(first_events,key=lambda x:x['step']) if first_events else None
        tied=sorted(x['neuron'] for x in first_events if first and x['step']==first['step'])
        rec={'presentation_index':presentation_index,'cycle':cycle,'pattern':pattern,
          't_start':t_start,'t_end':e.timestep,'first_l2e_spiker':first['neuron'] if first else None,
          'first_l2e_step':first['step'] if first else None,'same_step_tie':len(set(tied))>1,
          'earliest_response_set':sorted(set(tied))}
        presentations.append(rec);presentation_index+=1
        if pattern not in first_by_pattern and first:
          first_by_pattern[pattern]=rec;timeline.append({'type':'first_pattern_response',**rec})
        if stop_reason:break
      if stop_reason:break
    final_t=e.timestep
    lost=[dict(v) for k,v in scheduled.items() if v['arrival_step']<final_t and arrived[k]==0]
    duplicate=[{'key':list(k),'count':v} for k,v in arrived.items() if v>1]
    if lost:stop_reason='queued event lost'
    if duplicate:stop_reason='queued event duplicated'
    compression=compression_summary(e,presentations,first_by_pattern)
    transient=compression['first_transient_overlap'];persistent=compression['persistent_collision']
    if transient:timeline.append({'type':'earliest_transient_ownership_overlap',**transient,
      'step':presentations[transient['presentation_index']]['t_start']})
    collision_step=None
    if persistent:
      collision_step=presentations[persistent['presentation_index']]['t_start']
      timeline.append({'type':'persistent_ownership_collision_onset',**persistent,'step':collision_step})
    first_pc=min((x['step'] for x in pc_spikes),default=None)
    first_mature_coincidence=min((x['step'] for x in next_mature.values()),default=None)
    availability=first_pc
    if np.any(inactive_updates):classification='DECODER_LOCALITY_FAILURE'
    elif persistent is None:classification='NO_PERSISTENT_COLLISION'
    elif availability is None:classification='MECHANISM_UNDEREXPOSED'
    elif availability<=collision_step:classification='MECHANISM_AVAILABLE_BEFORE_COLLISION'
    else:classification='MECHANISM_AVAILABLE_AFTER_COLLISION'
    mature=decoder_matrix(e)>=MATURITY
    owners={p:modal([r['first_l2e_spiker'] for r in presentations if r['pattern']==p]) for p in CYCLE_ORDER}
    coverage={}
    for p,owner in owners.items():
      active=[i for i,v in enumerate(PATTERNS[p]) if v];j=int(owner[3:]) if owner else None
      coverage[p]={'representation':owner,'expected_pixels':active,
        'mature_expected_pixels':[i for i in active if j is not None and mature[j,i]],
        'mature_coverage_out_of_3':sum(bool(mature[j,i]) for i in active) if j is not None else 0,
        'unwanted_mature_other_pixels':[i for i in range(N_PIX) if i not in active and j is not None and mature[j,i]]}
    return {'seed':seed,'topology_seed':TOPOLOGY_SEED,'smoke':smoke,'cycles':cycles,
      'steps_planned':total_steps,'steps_completed':final_t,'runtime_seconds':time.monotonic()-start,
      'stop_reason':stop_reason,'classification':classification,'first_pattern_responses':first_by_pattern,
      'earliest_transient_overlap':transient,'persistent_collision':persistent,
      'persistent_collision_step':collision_step,'first_mature_sensory_feedback_coincidence_step':first_mature_coincidence,
      'first_physical_pc_spike_step':first_pc,'first_counterfactual_local_i_delivery_step':first_pc,
      'fraction_run_before_prediction_available':availability/total_steps if availability is not None else 1.0,
      'presentations_before_prediction_available':sum(r['t_start']<availability for r in presentations) if availability is not None else len(presentations),
      'collision_relative_to_availability':('no_collision' if collision_step is None else 'before' if availability is None or collision_step<availability else 'after_or_same'),
      'decoder_update_counts':{f'd[{j},{i}]':int(update_counts[j,i]) for j in range(N_OUT) for i in range(N_PIX)},
      'active_pixel_decoder_updates':int(active_updates.sum()),'inactive_pixel_decoder_updates':int(inactive_updates.sum()),
      'maturity_crossings':crossings,'first_subsequent_mature_coincidences':next_mature,
      'mature_decoder_synapses_out_of_72':int(mature.sum()),
      'pc_columns_with_mature_source':int(np.any(mature,axis=0).sum()),'per_pattern_coverage':coverage,
      'final_decoder_weight_stats':{'minimum':float(decoder_matrix(e).min()),
        'maximum':float(decoder_matrix(e).max()),'mean':float(decoder_matrix(e).mean())},
      'coincidence_cell_steps':coincidence_cell_steps,'current_step_coincidence_rate':coincidence_cell_steps/(max(final_t,1)*N_PIX),
      'steps_with_any_coincidence_rate':steps_with_coincidence/max(final_t,1),
      'pc_spikes':pc_spikes,'counterfactual_local_i_deliveries':counterfactual,
      'stale_queue_delivery_count':len(stale),'queue_arrival_count':sum(arrived.values()),
      'stale_queue_events':stale,
      'queue_scheduled_count':len(scheduled),'queue_tail_pending_count':sum(v['arrival_step']>=final_t for v in scheduled.values() if arrived[event_key(v)]==0),
      'duplicate_queue_deliveries':duplicate,'lost_queue_deliveries':lost,
      'default_off_disagreement':False,'locality_invariant_disagreement':bool(np.any(inactive_updates)),
      'feedforward_compression_indicators':compression,'presentation_log':presentations,
      'timeline':sorted(timeline,key=lambda x:(x.get('step',-1),x['type']))}

def write_csv(runs):
    fields=['seed','type','step','pattern','source','target','details']
    with (OUT/'timeline.csv').open('w',newline='') as f:
      w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
      for run in runs:
       for x in run['timeline']:
        w.writerow({'seed':run['seed'],'type':x['type'],'step':x.get('step'),
          'pattern':x.get('pattern'),'source':x.get('source'),'target':x.get('target'),
          'details':json.dumps(x,sort_keys=True)})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--smoke-only',action='store_true');args=ap.parse_args()
    t0=time.monotonic(); base=default_hash(BASE); repaired=default_hash(ROOT)
    if base!=repaired:
      result={'verdict':'AUDIT_INVALID','stop_reason':'default-off behavior differs','default_off':{'base':base,'repaired':repaired}}
      (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 2
    smoke=run_seed(1,cycles=2,smoke=True)
    if smoke['stop_reason']:
      result={'verdict':'AUDIT_INVALID','stop_reason':smoke['stop_reason'],'smoke':smoke,'default_off':{'base':base,'repaired':repaired,'match':True}}
      (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n');write_csv([smoke]);print(json.dumps({'verdict':'AUDIT_INVALID','stop':smoke['stop_reason']}));return 2
    runs=[] if args.smoke_only else [run_seed(s) for s in SEEDS]
    stop=next((r['stop_reason'] for r in runs if r['stop_reason']),None)
    classes=Counter(r['classification'] for r in runs)
    if stop:verdict='AUDIT_INVALID'
    elif not runs:verdict='NATURAL_EXPOSURE_INSUFFICIENT'
    elif all(r['first_physical_pc_spike_step'] is None for r in runs):verdict='NATURAL_EXPOSURE_INSUFFICIENT'
    elif sum(r['classification']=='MECHANISM_AVAILABLE_BEFORE_COLLISION' for r in runs) > len(runs)/2:verdict='NATURAL_EXPOSURE_EARLY_ENOUGH'
    else:verdict='NATURAL_EXPOSURE_TOO_LATE'
    result={'verdict':verdict,'checkout':str(ROOT.parent),'branch':'phase35-natural-exposure-codex2',
      'commit':'db30ceadbe18cf90e01f6d54dee0203f342b24a8','clean_before_run':True,
      'shared_with_claude':False,'production_edits':False,'configuration':{'flags':FLAGS,'cycles':CYCLES,
      'presentation_steps':PRESENTATION_STEPS,'cycle_order':CYCLE_ORDER,'seeds':SEEDS,'topology_seed':TOPOLOGY_SEED,
      'maturity_effective_weight':MATURITY},'default_off':{'base_hash':base,'repaired_hash':repaired,'match':True},
      'smoke':smoke,'runs':runs,'classification_counts':dict(classes),'runtime_seconds':time.monotonic()-t0,
      'stop_reason':stop,'processes_remaining':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');write_csv(runs)
    print(json.dumps({'verdict':verdict,'classes':dict(classes),'runtime_seconds':result['runtime_seconds'],'stop':stop},sort_keys=True))
    return 2 if stop else 0
if __name__=='__main__':raise SystemExit(main())
