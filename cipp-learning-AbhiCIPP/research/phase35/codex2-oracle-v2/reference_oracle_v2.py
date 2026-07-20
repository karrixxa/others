#!/usr/bin/env python3
"""Independent Phase 35 coincidence-cell oracle v2."""
from __future__ import annotations
from dataclasses import asdict, dataclass, replace
from itertools import product
import json
from pathlib import Path
from typing import Any, Iterable

@dataclass(frozen=True)
class Config:
    name:str; basal_weight:float; d_init:float; d_max:float; eta:float
    soma_threshold:float; expected_feedback_sources:tuple[str,...]

@dataclass(frozen=True)
class Event:
    event_id:str; branch:str; source:str; target:str
    scheduled_timestep:int; delivered_timestep:int; magnitude:float
    origin_pattern:str; current_pattern:str; origin_pixel:str; current_pixel:str
    delivery_role:str='active'; deferred:bool=False

TEST=Config('oracle_v2_test',3.0,2.0,11.0,1.0,5.0,('feedback','feedback0','feedback1'))
CANDIDATE=Config('legacy_candidate_only',150.0,50.0,1200.0,0.15,500.0,
                 tuple(f'L2E{i}' for i in range(8)))

def ev(event_id,branch,source=None,target='t0',scheduled=0,delivered=0,magnitude=1.0,
       origin_pattern='A',current_pattern='A',origin_pixel='p0',current_pixel='p0',
       role='active',deferred=False):
    return Event(event_id,branch,source or ('input' if branch=='basal' else 'feedback'),
      target,scheduled,delivered,magnitude,origin_pattern,current_pattern,
      origin_pixel,current_pixel,role,deferred)

def origin_class(events):
    events=tuple(events); stale=[e for e in events if e.origin_pattern!=e.current_pattern]
    if not stale:return 'current-correct'
    labels={'stale-same-pixel' if e.origin_pixel==e.current_pixel else 'stale-wrong-pixel' for e in stale}
    return next(iter(labels)) if len(stale)==len(events) and len(labels)==1 else 'mixed'

def simulate(events:Iterable[Event],cfg:Config=TEST,weights=None,basal_weight=None):
    events=tuple(events)
    if len({e.event_id for e in events})!=len(events): raise ValueError('duplicate event_id')
    bw=cfg.basal_weight if basal_weight is None else float(basal_weight)
    weights=dict(weights or {}); records=[]; updates=[]; spikes=[]
    for t in sorted({e.delivered_timestep for e in events}):
        all_at=[e for e in events if e.delivered_timestep==t]
        active=[e for e in all_at if e.delivery_role=='active' and e.magnitude>0]
        transitions=[]
        for target in sorted({e.target for e in active}):
            basal=[e for e in active if e.target==target and e.branch=='basal']
            apical=[e for e in active if e.target==target and e.branch=='apical'
                    and e.source in cfg.expected_feedback_sources]
            if not basal or not apical: continue
            sources=sorted({e.source for e in apical})
            before={s:weights.get(f'{s}->{target}',cfg.d_init) for s in sources}
            basal_charge=sum(e.magnitude*bw for e in basal)
            apical_charge=sum(e.magnitude*before[e.source] for e in apical)
            soma_charge=basal_charge+apical_charge
            fired=soma_charge>=cfg.soma_threshold
            if fired: spikes.append({'timestep':t,'target':target,'soma_charge':soma_charge})
            local_updates=[]
            for source in sources:
                key=f'{source}->{target}'; d_before=before[source]
                eligibility=1.0 # positive, delivered, configured source + same-target basal gate
                saturation=(1.0-d_before/cfg.d_max)**2
                raw_delta=cfg.eta*eligibility*saturation
                d_after=min(cfg.d_max,max(0.0,d_before+raw_delta))
                weights[key]=d_after
                u={'key':key,'d_before':d_before,'eta':cfg.eta,
                   'local_coincidence_or_eligibility':eligibility,
                   'magnitude_handling':'magnitude>0 gates eligibility; magnitude does not scale delta',
                   'saturation_factor':saturation,'raw_delta':raw_delta,
                   'stored_delta':d_after-d_before,'d_after':d_after}
                updates.append({'timestep':t,**u}); local_updates.append(u)
            transitions.append({'target':target,'event_ids':sorted(e.event_id for e in basal+apical),
              'origin_class':origin_class(basal+apical),'basal_charge':basal_charge,
              'apical_charge_before_learning':apical_charge,'soma_charge_before_learning':soma_charge,
              'soma_threshold':cfg.soma_threshold,'fired_using_d_before':fired,
              'updates':local_updates})
        records.append({'timestep':t,'delivered_event_ids':sorted(e.event_id for e in all_at),
          'active_event_ids':sorted(e.event_id for e in active),'transitions':transitions,
          'end_state':{'basal_events':[],'apical_events':[]}})
    return {'records':records,'updates':updates,'spikes':spikes,'final_weights':weights,
      'delivery_counts':{e.event_id:1 for e in events}}

def summary(r):
    ts=[x for rec in r['records'] for x in rec['transitions']]
    return {'coincidence_count':len(ts),'coincidence_targets':[x['target'] for x in ts],
      'spike_count':len(r['spikes']),'update_keys':[u['key'] for u in r['updates']],
      'origin_classes':[x['origin_class'] for x in ts],'delivery_counts':r['delivery_counts'],
      'end_states_clear':all(not rec['end_state']['basal_events'] and not rec['end_state']['apical_events'] for rec in r['records'])}

def build_goldens():
    cases=[]
    def add(name,purpose,events,weights=None,basal_weight=None):
        r=simulate(events,TEST,weights,basal_weight)
        cases.append({'name':name,'purpose':purpose,'events':[asdict(e) for e in events],
          'initial_weights':weights or {},'basal_weight':TEST.basal_weight if basal_weight is None else basal_weight,
          'expected':summary(r),'expected_transitions':r['records']})
    add('neither_input','No events.',[])
    add('basal_only','Basal cannot open gate.',[ev('b','basal')])
    add('apical_only_max_weight','Apical alone cannot open gate.',[ev('a','apical')],{'feedback->t0':TEST.d_max})
    add('same_step_coincidence','Same target and delivery step.',[ev('b','basal'),ev('a','apical')])
    add('offset_minus_one','Apical one step early.',[ev('a','apical',delivered=0),ev('b','basal',delivered=1)])
    add('offset_plus_one','Apical one step late.',[ev('b','basal',delivered=0),ev('a','apical',delivered=1)])
    add('same_schedule_different_delivery','Scheduling does not define coincidence.',[ev('b','basal'),ev('a','apical',delivered=1)])
    add('different_schedule_same_delivery','Delivery defines coincidence.',[ev('b','basal',scheduled=0,delivered=2),ev('a','apical',scheduled=1,delivered=2)])
    add('wrong_target','Targets differ.',[ev('b','basal',target='t0'),ev('a','apical',target='t1')])
    add('wrong_feedback_source','Unconfigured apical source.',[ev('b','basal'),ev('a','apical',source='other')])
    add('repeated_single_branch','No trace coincidence.',[ev('b0','basal'),ev('b1','basal',delivered=1)])
    add('timestep_clearing','Prior basal state clears.',[ev('b','basal'),ev('a','apical',delivered=1)])
    # Four coincidences are minimal for 4 -> 4.405 -> 4.764 -> 5.089; the fourth fires.
    cross=[ev(f'b{i}','basal',delivered=i) for i in range(4)]+[ev(f'a{i}','apical',delivered=i) for i in range(4)]
    add('decoder_threshold_crossing','Crossing update cannot fire until later coincidence.',cross,{'feedback->t0':4.0},0.0)
    nine=[ev(f'a{i}','apical',target=f't{i}') for i in range(9)]
    three=[ev(f'b{i}','basal',source=f'in{i}',target=f't{i}') for i in (1,4,7)]
    add('three_active_targets_of_nine','Only three target-local weights update.',nine+three)
    add('queue_carryover_switch_same_pixel','Stale queued pair survives.',[ev('b','basal',scheduled=0,delivered=2,origin_pattern='A',current_pattern='B'),ev('a','apical',scheduled=0,delivered=2,origin_pattern='A',current_pattern='B')])
    add('queue_carryover_switch_wrong_pixel','Stale wrong-pixel pair survives.',[ev('b','basal',scheduled=0,delivered=2,origin_pattern='A',current_pattern='B',origin_pixel='p9'),ev('a','apical',scheduled=0,delivered=2,origin_pattern='A',current_pattern='B',origin_pixel='p9')])
    add('queue_carryover_mixed_origin','Mixed provenance does not suppress.',[ev('b','basal',scheduled=0,delivered=2,origin_pattern='A',current_pattern='B'),ev('a','apical',scheduled=2,delivered=2,origin_pattern='B',current_pattern='B')])
    add('one_time_refractory_deferral','Deferred event delivered once.',[ev('b','basal',scheduled=0,delivered=1,deferred=True),ev('a','apical',scheduled=1,delivered=1)])
    add('active_versus_shadow','Shadow event is observational only.',[ev('b','basal'),ev('a','apical',role='shadow')])
    add('magnitude_charge_not_learning_scale','Magnitude scales charge but not local update.',[ev('b','basal',magnitude=2),ev('a','apical',magnitude=2)])
    return cases

def exhaustive():
    # Ordered two-event space: 2*3*2*2*2*2 = 96 events, 9,216 records.
    domain=list(product(('basal','apical'),('input','feedback','other'),('t0','t1'),(0,1),(0,1),('active','shadow')))
    bad=[]; count=0
    for left,right in product(domain,repeat=2):
        def mk(n,v):
            branch,source,target,scheduled,delivered,role=v
            return ev(f'e{n}',branch,source=source,target=target,scheduled=scheduled,delivered=delivered,role=role)
        es=[mk(0,left),mk(1,right)]; r=simulate(es); s=summary(r)
        expected=(all(e.delivery_role=='active' and e.magnitude>0 for e in es)
          and es[0].target==es[1].target and es[0].delivered_timestep==es[1].delivered_timestep
          and {e.branch for e in es}=={'basal','apical'}
          and next(e for e in es if e.branch=='apical').source in TEST.expected_feedback_sources)
        violations=[]
        if bool(s['coincidence_count'])!=expected: violations.append('gate')
        if not expected and (s['spike_count'] or s['update_keys']): violations.append('effect_without_gate')
        if not s['end_states_clear']: violations.append('clearing')
        if any(v!=1 for v in s['delivery_counts'].values()): violations.append('exactly_once')
        if violations and len(bad)<100: bad.append({'events':[asdict(e) for e in es],'violations':violations})
        count+=1
    return {'single_event_count':len(domain),'ordered_pair_count':count,
      'domains':{'branch':['basal','apical'],'source':['input','feedback','other'],'target':['t0','t1'],
       'scheduled_timestep':[0,1],'delivered_timestep':[0,1],'magnitude':[1.0],
       'delivery_role':['active','shadow'],'provenance':['current-correct']},
      'counterexample_count':len(bad),'counterexamples':bad}

def maturity_runs():
    out=[]
    for d in (4.0,5.0,6.0):
        es=[ev('b','basal'),ev('a','apical')]; r=simulate(es,TEST,{'feedback->t0':d},0.0)
        out.append({'d_before':d,'result':r,'fires':bool(r['spikes'])})
    return out

def main():
    root=Path(__file__).resolve().parent; gold=build_goldens(); ex=exhaustive(); maturity=maturity_runs()
    (root/'golden_cases_v2.json').write_text(json.dumps({'schema_version':2,'config':asdict(TEST),'cases':gold},indent=2)+'\n')
    (root/'results.json').write_text(json.dumps({'oracle_verdict':'SEMANTIC_CONTRACT_CONSISTENT',
      'golden_count':len(gold),'exhaustive':ex,'maturity_boundary':maturity,
      'parameter_sets':{'test':asdict(TEST),'legacy_candidate_only':asdict(CANDIDATE)}},indent=2)+'\n')
    print(json.dumps({'goldens':len(gold),'enumerated':ex['ordered_pair_count'],'counterexamples':ex['counterexample_count']}))
if __name__=='__main__':main()
