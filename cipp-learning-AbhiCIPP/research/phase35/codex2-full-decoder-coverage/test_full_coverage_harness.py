import importlib.util,sys
from pathlib import Path
P=Path(__file__).with_name('run_full_coverage.py')
spec=importlib.util.spec_from_file_location('coverage',P);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def test_fixed_configuration():
    assert m.BASE_CHECKPOINTS==[25600,51200] and m.EXTENDED==102400
    assert m.SEEDS==[1,2,3,4,5] and m.MATURITY==350
    assert m.FLAGS['prediction_column_enabled'] and not m.FLAGS['prediction_column_to_i_enabled']
    assert not m.FLAGS['loser_depression'] and not m.FLAGS['l2e_budget']
def test_clean_decoder_definition():
    import numpy as np
    w=np.zeros((m.N_OUT,m.N_PIX));w[2,[2,4,6]]=m.MATURITY
    assert m.clean_map(w)=={'L2E2':'diag /'}
    w[2,3]=m.MATURITY
    assert m.clean_map(w)=={}
