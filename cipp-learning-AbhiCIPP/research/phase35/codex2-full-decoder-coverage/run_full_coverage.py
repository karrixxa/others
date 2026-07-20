#!/usr/bin/env python3
"""Passive full-decoder coverage and retention experiment."""
from __future__ import annotations
import json,sys,time
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np

ROOT=Path('/home/cxiong/codex-runs/codex2-phase35-natural-exposure-checkout/cipp-learning-AbhiCIPP')
OUT=Path('/home/cxiong/codex-runs/codex2-phase35-full-decoder-coverage')
sys.path.insert(0,str(ROOT))
from backend.simulation import SimulationEngine,PATTERNS,N_OUT,N_PIX
from backend.presets import DASHBOARD_PRESET
from diagnostic_schedule import CYCLE_ORDER,PRESENTATION_STEPS
from phase27_l2_ownership_causal_audit import find_persistent_ownership_collision

SEEDS=[1,2,3,4,5];TOPOLOGY_SEED=1;BASE_CHECKPOINTS=[25600,51200];EXTENDED=102400
FLAGS=dict(DASHBOARD_PRESET)
FLAGS.update(prediction_column_enabled=True,prediction_column_to_i_enabled=False,
 confidence_consolidation=False,loser_depression=False,l2e_budget=False,homeostasis=False)
MATURITY=float(FLAGS.get('prediction_threshold',500)-FLAGS.get('prediction_lateral_weight',150))
SETS={p:{i for i,v in enumerate(PATTERNS[p]) if v} for p in CYCLE_ORDER}

def matrix(e):return np.array([pc.decoder_weights for pc in e.pcol],dtype=float).T
def modal(xs):
    c=Counter(x for x in xs if x is not None)
    if not c:return None
    n=max(c.values());return min(k for k,v in c.items() if v==n)
def source_class(pixels):
    x=set(pixels);full=sorted(p for p,s in SETS.items() if s<=x)
    if not x:return 'IMMATURE',[]
    if x=={4}:return 'CENTER_ONLY',[]
    if len(full)>=2:return 'MULTI_PATTERN_UNION',full
    if len(full)==1 and x==SETS[full[0]]:return 'COMPLETE_SINGLE_PATTERN',full
    containers=sorted(p for p,s in SETS.items() if x<s)
    if len(containers)==1:return 'PARTIAL_SINGLE_PATTERN',containers
    return 'SCATTERED_FRAGMENT',full
def clean_map(w):
    out={}
    for j in range(N_OUT):
        pixels={i for i in range(N_PIX) if w[j,i]>=MATURITY};cls,pats=source_class(pixels)
        if cls=='COMPLETE_SINGLE_PATTERN':out[f'L2E{j}']=pats[0]
    return out
def ownership(log):return {p:modal([r['first_l2e_spiker'] for r in log if r['pattern']==p]) for p in CYCLE_ORDER}
def ownership_changes(log):
    hist=defaultdict(list);last={};n=Counter()
    for r in log:
        p=r['pattern'];hist[p].append(r['first_l2e_spiker']);m=modal(hist[p])
        if p in last and last[p]!=m:n[p]+=1
        last[p]=m
    return {'total':sum(n.values()),'per_pattern':{p:n[p] for p in CYCLE_ORDER}}

def checkpoint(e,step,log,updates,first_complete,gains,losses,pc_spikes):
    w=matrix(e);clean=clean_map(w);owners=ownership(log)
    covered=sorted(set(clean.values()));by_pattern={p:sorted(s for s,q in clean.items() if q==p) for p in CYCLE_ORDER}
    collision=find_persistent_ownership_collision(log);collision_step=None
    if collision:collision_step=log[collision['presentation_index']]['t_start']
    sources=[]
    for j in range(N_OUT):
        pixels=[i for i in range(N_PIX) if w[j,i]>=MATURITY];cls,pats=source_class(pixels);src=f'L2E{j}'
        sources.append({'source':src,'weights':[float(x) for x in w[j]],'mature_pixels':pixels,
          'classification':cls,'pattern_candidates':pats,'clean_pattern':clean.get(src),
          'owned_patterns':sorted(p for p,o in owners.items() if o==src),
          'selectivity_agrees':clean.get(src) is None or owners.get(clean[src])==src,
          'updates_by_pixel':[int(updates[j,i]) for i in range(N_PIX)],'total_updates':int(updates[j].sum())})
    uncovered=sorted(set(CYCLE_ORDER)-set(covered));starvation={}
    for p in uncovered:
        owner=owners.get(p);j=int(owner[3:]) if owner else None;active=sorted(SETS[p])
        credit=[int(updates[k,active].sum()) for k in range(N_OUT)];best=int(np.argmax(credit))
        starvation[p]={'modal_owner':owner,'active_pixels':active,
          'owner_active_pixel_weights':[float(w[j,i]) for i in active] if j is not None else None,
          'owner_missing_mature_pixels':[i for i in active if j is None or w[j,i]<MATURITY],
          'owner_active_pixel_updates':credit[j] if j is not None else None,
          'highest_credit_source':f'L2E{best}','highest_credit_active_pixel_updates':credit[best],
          'modal_owner_is_persistent_collided_source':bool(collision and owner==collision['neuron']),
          'competing_source_has_more_credit':bool(j is not None and credit[best]>credit[j])}
    mature=(w>=MATURITY)
    return {'step':step,'complete_single_pattern_decoders':len(clean),
      'distinct_patterns_covered_out_of_4':len(covered),'patterns_covered':covered,
      'patterns_uncovered':uncovered,'clean_decoders_by_pattern':by_pattern,
      'four_complete_decoders_use_distinct_sources':len(covered)==4 and len(clean)>=4,
      'all_clean_decoders_agree_with_observed_ownership':all(owners.get(p)==s for s,p in clean.items()),
      'observed_modal_ownership':owners,'first_complete_decoder_step_by_pattern':dict(first_complete),
      'complete_decoder_gain_events':list(gains),'complete_decoder_loss_events':list(losses),
      'any_complete_decoder_later_lost':bool(losses),
      'mature_center_synapses':int(mature[:,4].sum()),
      'mature_peripheral_synapses':int(mature.sum()-mature[:,4].sum()),
      'persistent_ownership_collision':collision,'persistent_collision_step':collision_step,
      'ownership_changes':ownership_changes(log),'uncovered_pattern_starvation':starvation,
      'counterfactual_active_mode_pc_spikes':pc_spikes,'sources':sources}

def run_seed(seed):
    start=time.monotonic();e=SimulationEngine(**dict(FLAGS,seed=seed,topology_seed=TOPOLOGY_SEED))
    updates=np.zeros((N_OUT,N_PIX),int);prev=matrix(e);previous_clean={};first_complete={};gains=[];losses=[]
    log=[];pc_spikes=0;pidx=0;snapshots=[];target=51200
    for step0 in range(0,EXTENDED,PRESENTATION_STEPS):
        pattern=CYCLE_ORDER[(step0//PRESENTATION_STEPS)%4];cycle=(step0//PRESENTATION_STEPS)//4
        e.set_pattern(pattern);t_start=e.timestep;first=None;responders=[]
        for rel in range(PRESENTATION_STEPS):
            e.step();t=e.timestep-1;now=matrix(e)
            for j,i in np.argwhere(now!=prev):updates[int(j),int(i)]+=1
            clean=clean_map(now)
            for src,p in clean.items():
                if previous_clean.get(src)!=p:
                    ev={'step':t,'source':src,'pattern':p};gains.append(ev)
                    first_complete.setdefault(p,t)
            for src,p in previous_clean.items():
                if clean.get(src)!=p:losses.append({'step':t,'source':src,'pattern':p,
                  'new_state':source_class({i for i in range(N_PIX) if now[int(src[3:]),i]>=MATURITY})[0]})
            previous_clean=clean;prev=now
            pc_spikes+=sum(bool(e.spiked[f'PC{i}']) for i in range(N_PIX))
            fired=[f'L2E{j}' for j in range(N_OUT) if e.spiked[f'L2E{j}']]
            if fired and first is None:first=t;responders=sorted(fired)
        log.append({'presentation_index':pidx,'cycle':cycle,'pattern':pattern,'t_start':t_start,'t_end':e.timestep,
          'first_l2e_spiker':responders[0] if responders else None,'same_step_tie':len(responders)>1});pidx+=1
        if e.timestep in BASE_CHECKPOINTS:
            s=checkpoint(e,e.timestep,log,updates,first_complete,gains,losses,pc_spikes);snapshots.append(s)
            print(json.dumps({'seed':seed,'checkpoint':e.timestep,'complete':s['complete_single_pattern_decoders'],
              'patterns':s['patterns_covered'],'lost':len(losses),'pc_spikes':pc_spikes}),flush=True)
            if e.timestep==51200 and s['distinct_patterns_covered_out_of_4']==4 and s['four_complete_decoders_use_distinct_sources']:
                target=51200;break
            if e.timestep==51200:target=EXTENDED
        if e.timestep==EXTENDED:
            s=checkpoint(e,e.timestep,log,updates,first_complete,gains,losses,pc_spikes);snapshots.append(s)
            print(json.dumps({'seed':seed,'checkpoint':e.timestep,'complete':s['complete_single_pattern_decoders'],
              'patterns':s['patterns_covered'],'lost':len(losses),'pc_spikes':pc_spikes}),flush=True)
            break
    return {'seed':seed,'runtime_seconds':time.monotonic()-start,'extended_to_102400':target==EXTENDED,
      'checkpoints':snapshots,'final_step':snapshots[-1]['step']}

def main():
    t0=time.monotonic();runs=[]
    for seed in SEEDS:
        runs.append(run_seed(seed));(OUT/'partial_results.json').write_text(json.dumps({'runs':runs},indent=2,sort_keys=True)+'\n')
    finals=[r['checkpoints'][-1] for r in runs]
    all_four=all(x['distinct_patterns_covered_out_of_4']==4 for x in finals)
    distinct=all(x['four_complete_decoders_use_distinct_sources'] for x in finals)
    agree=all(x['all_clean_decoders_agree_with_observed_ownership'] for x in finals)
    extreme=any(r['extended_to_102400'] and r['checkpoints'][-1]['distinct_patterns_covered_out_of_4']==4 for r in runs)
    collision_blocks=any(x['patterns_uncovered'] and any(v['modal_owner_is_persistent_collided_source'] for v in x['uncovered_pattern_starvation'].values()) for x in finals)
    if all_four and distinct and agree:verdict='COVERAGE_REQUIRES_EXTREME_HORIZON' if extreme else 'ALL_FOUR_CLEAN_DECODERS_EMERGE_AND_PERSIST'
    elif all_four:verdict='ALL_FOUR_EMERGE_BUT_NOT_DISTINCT'
    elif collision_blocks:verdict='COLLISION_BLOCKS_COMPLETE_COVERAGE'
    else:verdict='PARTIAL_COVERAGE_PERSISTS'
    result={'verdict':verdict,'checkout':str(ROOT.parent),'commit':'db30ceadbe18cf90e01f6d54dee0203f342b24a8',
      'configuration':{'flags':FLAGS,'seeds':SEEDS,'topology_seed':TOPOLOGY_SEED,
        'base_checkpoints':BASE_CHECKPOINTS,'optional_checkpoint':EXTENDED,'presentation_steps':PRESENTATION_STEPS,
        'cycle_order':CYCLE_ORDER,'maturity_threshold':MATURITY},'runs':runs,
      'runtime_seconds':time.monotonic()-t0,'production_edits':False,'processes_remaining':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'runtime_seconds':result['runtime_seconds'],
      'extended_seeds':[r['seed'] for r in runs if r['extended_to_102400']]}),flush=True)
if __name__=='__main__':main()
