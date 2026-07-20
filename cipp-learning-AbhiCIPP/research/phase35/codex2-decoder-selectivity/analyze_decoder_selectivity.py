#!/usr/bin/env python3
"""Passive decoder assembly/selectivity analysis of frozen kinetics results."""
from __future__ import annotations
import json
from pathlib import Path

IN=Path('/home/cxiong/codex-runs/codex2-phase35-long-horizon-maturity/results.json')
OUT=Path('/home/cxiong/codex-runs/codex2-phase35-decoder-selectivity')
PATTERNS={'row 1':{3,4,5},'col 1':{1,4,7},'diag \\':{0,4,8},'diag /':{2,4,6}}
PIXEL_PATTERNS={i:sorted(p for p,s in PATTERNS.items() if i in s) for i in range(9)}
MATURITY=350.0

def classify(mature):
    mature=set(mature)
    if not mature:return 'IMMATURE'
    full=sorted(p for p,s in PATTERNS.items() if s<=mature)
    if mature=={4}:return 'CENTER_ONLY'
    if len(full)>=2:return 'MULTI_PATTERN_UNION'
    if len(full)==1 and mature==PATTERNS[full[0]]:return 'COMPLETE_SINGLE_PATTERN'
    containers=sorted(p for p,s in PATTERNS.items() if mature<s)
    if len(containers)==1:return 'PARTIAL_SINGLE_PATTERN'
    return 'SCATTERED_FRAGMENT'

def agreement(source,mature,classification,owners):
    owned=sorted(p for p,o in owners.items() if o==source);mature=set(mature)
    complete=sorted(p for p,s in PATTERNS.items() if s<=mature)
    if classification=='IMMATURE':return {'status':'NO_MATURE_DECODER','owned_patterns':owned}
    if classification=='CENTER_ONLY':return {'status':'NONSELECTIVE_CENTER_ONLY','owned_patterns':owned}
    if classification=='COMPLETE_SINGLE_PATTERN':
        p=complete[0];return {'status':'AGREES' if p in owned else 'DISAGREES','owned_patterns':owned,'decoder_patterns':[p]}
    compatible=sorted(p for p in owned if mature<=PATTERNS[p] or PATTERNS[p]<=mature)
    return {'status':'AGREES' if compatible else 'DISAGREES','owned_patterns':owned,
            'compatible_owned_patterns':compatible,'complete_decoder_patterns':complete}

def main():
    raw=json.loads(IN.read_text());seeds=[];all_classes={}
    for run in raw['runs']:
        final=run['checkpoints'][-1];flat=final['decoder_weight_distribution']['all_72']
        weights=[flat[j*9:(j+1)*9] for j in range(8)]
        owners=final['compression_indicators']['modal_owners'];decoders=[]
        update_by_source=[];total_updates=sum(final['updates_per_synapse'].values())
        collided_neuron=(final['persistent_collision'] or {}).get('neuron')
        for j in range(8):
            source=f'L2E{j}';mature=[i for i,w in enumerate(weights[j]) if w>=MATURITY]
            cls=classify(mature);full=sorted(p for p,s in PATTERNS.items() if s<=set(mature))
            partial=sorted(p for p,s in PATTERNS.items() if set(mature) and set(mature)<s)
            updates=[final['updates_per_synapse'][f'd[{j},{i}]'] for i in range(9)]
            count=sum(updates);update_by_source.append({'source':source,'updates':count,
              'fraction_of_seed_updates':count/total_updates if total_updates else 0.0})
            decoders.append({'source':source,'weights':[float(x) for x in weights[j]],
              'mature_pixels':mature,'mature_synapses':[{'pixel':i,'weight':float(weights[j][i]),
                 'trained_patterns':PIXEL_PATTERNS[i]} for i in mature],
              'classification':cls,'complete_patterns':full,'partial_container_patterns':partial,
              'complete_three_pixel_decoder':len(full)==1 and set(mature)==PATTERNS[full[0]],
              'shared_center_only':set(mature)=={4},
              'partial_pattern':cls=='PARTIAL_SINGLE_PATTERN',
              'multi_pattern_union':cls=='MULTI_PATTERN_UNION',
              'ownership_selectivity_agreement':agreement(source,mature,cls,owners),
              'updates_by_pixel':updates,'total_updates':count,
              'is_collided_owner':source==collided_neuron})
            all_classes[cls]=all_classes.get(cls,0)+1
        complete=[d for d in decoders if d['classification']=='COMPLETE_SINGLE_PATTERN']
        complete_patterns=sorted({p for d in complete for p in d['complete_patterns']})
        mature_center=sum(4 in d['mature_pixels'] for d in decoders)
        mature_peripheral=sum(sum(i!=4 for i in d['mature_pixels']) for d in decoders)
        collided_mature=sum(len(d['mature_pixels']) for d in decoders if d['is_collided_owner'])
        noncollided_mature=sum(len(d['mature_pixels']) for d in decoders if not d['is_collided_owner'])
        shares=[x['fraction_of_seed_updates'] for x in update_by_source]
        seeds.append({'seed':run['seed'],'step':final['step'],'modal_owners':owners,
          'persistent_collision':final['persistent_collision'],'decoders':decoders,
          'complete_pattern_decoders':len(complete),'distinct_patterns_with_complete_decoder':len(complete_patterns),
          'complete_patterns':complete_patterns,'complete_decoder_sources':[d['source'] for d in complete],
          'complete_decoders_have_distinct_sources':len({d['source'] for d in complete})==len(complete),
          'mature_center_synapses':mature_center,'mature_peripheral_synapses':mature_peripheral,
          'mature_synapses_collided_owner':collided_mature,
          'mature_synapses_noncollided_owners':noncollided_mature,
          'update_concentration_by_source':update_by_source,
          'update_concentration_hhi':sum(x*x for x in shares),
          'usable_pattern_level_prediction':bool(complete),
          'usable_complete_patterns':complete_patterns,
          'mature_synapse_count':sum(len(d['mature_pixels']) for d in decoders)})
    complete_total=sum(s['complete_pattern_decoders'] for s in seeds)
    verdict=('CLEAN_PATTERN_DECODERS_EMERGE' if complete_total and
      all(d['ownership_selectivity_agreement']['status']=='AGREES'
          for s in seeds for d in s['decoders'] if d['classification']=='COMPLETE_SINGLE_PATTERN')
      else 'PARTIAL_DECODERS_ONLY')
    result={'verdict':verdict,'source_results':str(IN),'production_rerun':False,
      'maturity_threshold':MATURITY,'pattern_pixels':{p:sorted(s) for p,s in PATTERNS.items()},
      'classification_rules':{
       'COMPLETE_SINGLE_PATTERN':'mature set equals exactly one trained three-pixel set',
       'PARTIAL_SINGLE_PATTERN':'nonempty mature set is a strict subset of exactly one pattern',
       'CENTER_ONLY':'only shared pixel 4 is mature',
       'MULTI_PATTERN_UNION':'mature set contains at least two complete trained patterns',
       'SCATTERED_FRAGMENT':'mature pixels span patterns without forming a clean supported category',
       'IMMATURE':'no mature synapse'},
      'seeds':seeds,'aggregate':{'decoder_class_counts':all_classes,
        'complete_pattern_decoders':complete_total,
        'seeds_with_usable_pattern_prediction':sum(s['usable_pattern_level_prediction'] for s in seeds),
        'mature_center_synapses':sum(s['mature_center_synapses'] for s in seeds),
        'mature_peripheral_synapses':sum(s['mature_peripheral_synapses'] for s in seeds),
        'production_reruns':0},'production_edits':False,'processes_remaining':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':verdict,'classes':all_classes,'complete':complete_total,
                      'usable_seeds':result['aggregate']['seeds_with_usable_pattern_prediction']},sort_keys=True))
if __name__=='__main__':main()
