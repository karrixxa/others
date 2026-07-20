import importlib.util,sys
from pathlib import Path
P=Path(__file__).with_name('run_long_horizon_maturity.py')
spec=importlib.util.spec_from_file_location('kinetics',P);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def test_fixed_configuration():
    assert m.CHECKPOINTS==[3200,6400,12800,25600]
    assert m.SEEDS==[1,2,3,4,5] and m.TOPOLOGY_SEED==1
    assert m.FLAGS['prediction_column_enabled'] and not m.FLAGS['prediction_column_to_i_enabled']
    assert not m.FLAGS['loser_depression'] and not m.FLAGS['l2e_budget']
def test_maturity_recurrence():
    assert m.REQUIRED_UPDATES==2946
    assert m.CROSSING_WEIGHT>=m.MATURITY
def test_projection_fragmentation():
    import numpy as np
    x=np.zeros((m.N_OUT,m.N_PIX),int);x[0,0]=100;x[1,0]=100
    p=m.projection(x,1000)['source_fragmentation_by_pixel']['PC0']
    assert p['fragmentation_factor_aggregate_over_best']==2.0
    assert p['projected_maturity_step_fastest_actual_source']==2*p['projected_maturity_step_consolidated_source']
