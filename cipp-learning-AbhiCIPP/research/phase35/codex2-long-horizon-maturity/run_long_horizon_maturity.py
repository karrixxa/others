#!/usr/bin/env python3
"""Measurement-only long-horizon Phase 35 decoder kinetics audit."""
from __future__ import annotations
import argparse,json,os,sys,time
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np

ROOT=Path('/home/cxiong/codex-runs/codex2-phase35-natural-exposure-checkout/cipp-learning-AbhiCIPP')
OUT=Path('/home/cxiong/codex-runs/codex2-phase35-long-horizon-maturity')
sys.path.insert(0,str(ROOT))
from backend.simulation import SimulationEngine,PATTERNS,N_OUT,N_PIX
from backend.presets import DASHBOARD_PRESET
from diagnostic_schedule import CYCLE_ORDER,PRESENTATION_STEPS
from phase27_l2_ownership_causal_audit import find_earliest_modal_collision,find_persistent_ownership_collision

SEEDS=[1,2,3,4,5];TOPOLOGY_SEED=1;CHECKPOINTS=[3200,6400,12800,25600]
FLAGS=dict(DASHBOARD_PRESET)
FLAGS.update(prediction_column_enabled=True,prediction_column_to_i_enabled=False,
 confidence_consolidation=False,loser_depression=False,l2e_budget=False,homeostasis=False)
THRESHOLD=float(FLAGS.get('prediction_threshold',500.0));BASAL=float(FLAGS.get('prediction_lateral_weight',150.0))
MATURITY=THRESHOLD-BASAL;D_INIT=float(FLAGS.get('prediction_feedback_init',50.0))
D_MAX=float(FLAGS.get('prediction_feedback_max',1200.0));ETA=float(FLAGS.get('prediction_learning_rate',0.15))

def required_updates():
    w=D_INIT;n=0
    while w<MATURITY:w=min(D_MAX,w+ETA*(1-w/D_MAX)**2);n+=1
    return n,w
REQUIRED_UPDATES,CROSSING_WEIGHT=required_updates()

def modal(xs):
    c=Counter(x for x in xs if x is not None)
    if not c:return None
    n=max(c.values());return min(k for k,v in c.items() if v==n)

def matrix(e):return np.array([pc.decoder_weights for pc in e.pcol],dtype=float).T
def qkey(r):return (r['source'],r['target'],r['target_compartment'],int(r['scheduled_step']),int(r['arrival_step']))

def ownership_changes(log):
    hist=defaultdict(list);last={};changes=Counter()
    for r in log:
        p=r['pattern'];hist[p].append(r['first_l2e_spiker']);m=modal(hist[p])
        if p in last and m!=last[p]:changes[p]+=1
        last[p]=m
    return {'per_pattern':{p:int(changes[p]) for p in CYCLE_ORDER},'total':int(sum(changes.values())),'modal_owners':last}

def compression(e,log):
    owners=ownership_changes(log);counts=Counter(r['first_l2e_spiker'] for r in log if r['first_l2e_spiker'])
    total=sum(counts.values());w=np.array([n._weights_array.copy() for n in e.l2.excitatory_neurons])
    status={f'L2E{j}':e._l2e_status(j)['status'] for j in range(N_OUT)}
    ratios={}
    for j in range(N_OUT):
        per=np.delete(w[j],4);ratios[f'L2E{j}']=float(w[j,4]/np.mean(per)) if np.mean(per)>0 else None
    return {'modal_owners':owners['modal_owners'],'ownership_changes':owners,
      'distinct_first_responders':len(counts),'first_responder_share':{k:v/total for k,v in counts.items()},
      'l2e_status':status,'active_count':sum(v=='active' for v in status.values()),
      'never_first_responder':sorted(set(f'L2E{j}' for j in range(N_OUT))-set(counts)),
      'center_peripheral_ratio':ratios,'earliest_transient_overlap':find_earliest_modal_collision(log),
      'persistent_collision':find_persistent_ownership_collision(log)}

def projection(update_counts,steps):
    rates=update_counts/steps;per={};finite=[]
    for j in range(N_OUT):
      for i in range(N_PIX):
        rate=float(rates[j,i]);projected=REQUIRED_UPDATES/rate if rate>0 else None
        per[f'd[{j},{i}]']={'updates':int(update_counts[j,i]),'rate_per_step':rate,
          'projected_maturity_step_stationary_rate':projected}
        if projected is not None:finite.append(projected)
    frag={}
    for i in range(N_PIX):
      counts=update_counts[:,i];aggregate=int(counts.sum());best=int(counts.max());credited=int(np.sum(counts>0))
      ideal=REQUIRED_UPDATES/(aggregate/steps) if aggregate else None
      actual=REQUIRED_UPDATES/(best/steps) if best else None
      frag[f'PC{i}']={'distinct_credited_sources':credited,'aggregate_updates':aggregate,
       'best_source_updates':best,'fragmentation_factor_aggregate_over_best':aggregate/best if best else None,
       'projected_maturity_step_consolidated_source':ideal,'projected_maturity_step_fastest_actual_source':actual,
       'projected_fragmentation_delay_steps':actual-ideal if actual is not None and ideal is not None else None}
    return {'required_updates_from_init':REQUIRED_UPDATES,'per_synapse':per,
      'earliest_projected_maturity_step':min(finite) if finite else None,'source_fragmentation_by_pixel':frag}

def snapshot(e,step,counts,active,inactive,first_maturity,maturity_by_synapse,pc_spikes,
             arrivals,stale,scheduled,arrived,log,credit_by_pattern):
    w=matrix(e);mature=w>=MATURITY;comp=compression(e,log);persistent=comp['persistent_collision']
    collision_step=None
    if persistent:collision_step=log[persistent['presentation_index']]['t_start']
    q=np.quantile(w,[0,.1,.25,.5,.75,.9,1])
    sources={f'PC{i}':int(np.sum(counts[:,i]>0)) for i in range(N_PIX)}
    pattern_credit={}
    for p in CYCLE_ORDER:
      arr=credit_by_pattern[p];tot=int(arr.sum());owner=comp['modal_owners'].get(p)
      oj=int(owner[3:]) if owner else None
      pattern_credit[p]={'total_updates':tot,'distinct_sources':int(np.sum(arr.sum(axis=1)>0)),
        'modal_owner':owner,'updates_to_modal_owner':int(arr[oj].sum()) if oj is not None else 0,
        'modal_owner_credit_fraction':float(arr[oj].sum()/tot) if oj is not None and tot else None}
    due_lost=sum(1 for k,r in scheduled.items() if r['arrival_step']<step and arrived[k]==0)
    duplicates=sum(1 for v in arrived.values() if v>1)
    return {'step':step,'mature_decoder_synapses_out_of_72':int(mature.sum()),
      'pc_columns_with_mature_source':int(np.any(mature,axis=0).sum()),'decoder_weight_distribution':{
       'minimum':float(q[0]),'p10':float(q[1]),'p25':float(q[2]),'median':float(q[3]),
       'p75':float(q[4]),'p90':float(q[5]),'maximum':float(q[6]),'mean':float(w.mean()),
       'all_72':[float(x) for x in w.flatten()]},
      'first_maturity_step':first_maturity,'maturity_steps_by_synapse':dict(maturity_by_synapse),
      'updates_per_synapse':{f'd[{j},{i}]':int(counts[j,i]) for j in range(N_OUT) for i in range(N_PIX)},
      'distinct_l2_sources_receiving_credit_per_pixel':sources,
      'active_pixel_updates':int(active.sum()),'inactive_pixel_updates':int(inactive.sum()),
      'pc_spikes':pc_spikes,'queue_arrivals':arrivals,'stale_arrivals':stale,
      'stale_arrival_rate':stale/arrivals if arrivals else 0.0,'lost_due_queue_events':due_lost,
      'duplicate_queue_events':duplicates,'persistent_collision':persistent,'persistent_collision_step':collision_step,
      'ownership_changes':comp['ownership_changes'],'compression_indicators':comp,
      'credit_fragmentation_by_pattern':pattern_credit,'kinetic_projection':projection(counts,step)}

def run_seed(seed,checkpoints):
    start=time.monotonic();e=SimulationEngine(**dict(FLAGS,seed=seed,topology_seed=TOPOLOGY_SEED))
    counts=np.zeros((N_OUT,N_PIX),int);active=np.zeros_like(counts);inactive=np.zeros_like(counts)
    first_maturity=None;maturity_by={};pc_spikes=0;arrivals=stale=0;scheduled={};arrived=Counter()
    log=[];credit=defaultdict(lambda:np.zeros((N_OUT,N_PIX),int));snaps=[];pidx=0
    max_step=max(checkpoints)
    for step0 in range(0,max_step,PRESENTATION_STEPS):
      pattern=CYCLE_ORDER[(step0//PRESENTATION_STEPS)%len(CYCLE_ORDER)];cycle=(step0//PRESENTATION_STEPS)//len(CYCLE_ORDER)
      e.set_pattern(pattern);first=None;response_set=[];t_start=e.timestep
      for rel in range(PRESENTATION_STEPS):
        before=matrix(e);e.step();t=e.timestep-1;after=matrix(e)
        deliveries=e._prediction_column_last_deliveries
        meta=defaultdict(list)
        for r in deliveries:
          arrivals+=1;arrived[qkey(r)]+=1
          if r.get('origin_pattern')!=e.current_pattern:stale+=1
          meta[(r['source'],r['target'])].append(r)
        for slot in e.pcol_delivery_metadata_queue:
          for r in slot:scheduled.setdefault(qkey(r),dict(r))
        for j,i in np.argwhere(after!=before):
          j=int(j);i=int(i);counts[j,i]+=1
          origins={r.get('origin_pattern') for r in meta[(f'L2E{j}',f'PC{i}')] if r.get('origin_pattern') in PATTERNS}
          good=bool(origins) and all(PATTERNS[p][i] for p in origins)
          if good:
            active[j,i]+=1
            for p in origins:credit[p][j,i]+=1
          else:inactive[j,i]+=1
          key=f'd[{j},{i}]'
          if before[j,i]<MATURITY<=after[j,i] and key not in maturity_by:
            maturity_by[key]={'step':t,'d_before':float(before[j,i]),'d_after':float(after[j,i]),
              'crossing_step_pc_spike':bool(e.spiked[f'PC{i}'])}
            if first_maturity is None:first_maturity=t
        pc_spikes+=sum(bool(e.spiked[f'PC{i}']) for i in range(N_PIX))
        fired=[f'L2E{j}' for j in range(N_OUT) if e.spiked[f'L2E{j}']]
        if fired and first is None:first=t;response_set=sorted(fired)
      log.append({'presentation_index':pidx,'cycle':cycle,'pattern':pattern,'t_start':t_start,'t_end':e.timestep,
        'first_l2e_spiker':response_set[0] if response_set else None,'first_l2e_step':first,
        'same_step_tie':len(response_set)>1,'earliest_response_set':response_set});pidx+=1
      if e.timestep in checkpoints:
        s=snapshot(e,e.timestep,counts,active,inactive,first_maturity,maturity_by,pc_spikes,
          arrivals,stale,scheduled,arrived,log,credit);snaps.append(s)
        print(json.dumps({'seed':seed,'checkpoint':e.timestep,'mature':s['mature_decoder_synapses_out_of_72'],
          'max_weight':s['decoder_weight_distribution']['maximum'],'pc_spikes':pc_spikes,
          'collision_step':s['persistent_collision_step']}),flush=True)
        if s['inactive_pixel_updates'] or s['lost_due_queue_events'] or s['duplicate_queue_events']:
          return {'seed':seed,'runtime_seconds':time.monotonic()-start,'checkpoints':snaps,
            'stop_reason':'locality or queue invariant failure'}
    final=snaps[-1];collision=final['persistent_collision_step']
    if first_maturity is None:classification='no_maturity'
    elif collision is None or first_maturity<=collision:classification='maturity_before_collision'
    else:classification='maturity_after_collision'
    return {'seed':seed,'runtime_seconds':time.monotonic()-start,'checkpoints':snaps,
      'first_maturity_step':first_maturity,'persistent_collision_step':collision,
      'maturity_vs_collision':classification,'stop_reason':None}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--extend-51200',action='store_true');args=ap.parse_args()
    checkpoints=CHECKPOINTS+[51200] if args.extend_51200 else CHECKPOINTS;t0=time.monotonic();runs=[]
    for seed in SEEDS:
      runs.append(run_seed(seed,checkpoints))
      partial={'status':'running','runs':runs,'checkpoints':checkpoints}
      (OUT/'partial_results.json').write_text(json.dumps(partial,indent=2,sort_keys=True)+'\n')
      if runs[-1]['stop_reason']:break
    invalid=next((r['stop_reason'] for r in runs if r['stop_reason']),None)
    matured=[r for r in runs if r.get('first_maturity_step') is not None]
    before=[r for r in matured if r['maturity_vs_collision']=='maturity_before_collision']
    after=[r for r in matured if r['maturity_vs_collision']=='maturity_after_collision']
    if invalid:verdict='AUDIT_INVALID'
    elif not matured:verdict='MATURITY_HORIZON_EXCEEDS_TEST'
    elif before and not after:verdict='EVENTUAL_NATURAL_MATURITY_BEFORE_COLLISION'
    elif after and not before:verdict='EVENTUAL_NATURAL_MATURITY_AFTER_COLLISION'
    else:verdict='MIXED_MATURITY_FAILURE'
    result={'verdict':verdict,'checkout':str(ROOT.parent),'branch':'phase35-natural-exposure-codex2',
      'commit':'db30ceadbe18cf90e01f6d54dee0203f342b24a8','configuration':{'flags':FLAGS,
       'seeds':SEEDS,'topology_seed':TOPOLOGY_SEED,'checkpoints':checkpoints,'cycle_order':CYCLE_ORDER,
       'presentation_steps':PRESENTATION_STEPS,'maturity_weight':MATURITY,'required_updates_from_init':REQUIRED_UPDATES,
       'crossing_weight_after_required_updates':CROSSING_WEIGHT},'runs':runs,
      'runtime_seconds':time.monotonic()-t0,'extended_to_51200':args.extend_51200,
      'stop_reason':invalid,'production_edits':False,'processes_remaining':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'runtime_seconds':result['runtime_seconds'],
      'matured_seeds':len(matured),'before':len(before),'after':len(after),'stop':invalid}),flush=True)
    return 2 if invalid else 0
if __name__=='__main__':raise SystemExit(main())
