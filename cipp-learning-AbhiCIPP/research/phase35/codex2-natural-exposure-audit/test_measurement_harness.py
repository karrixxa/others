import importlib.util,sys
from pathlib import Path
P=Path(__file__).with_name('run_natural_exposure_audit.py')
spec=importlib.util.spec_from_file_location('audit_harness',P);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def test_shadow_flags():
    assert m.FLAGS['prediction_column_enabled'] is True
    assert m.FLAGS['prediction_column_to_i_enabled'] is False
    assert m.FLAGS['loser_depression'] is False
    assert m.FLAGS['l2e_budget'] is False
    assert m.FLAGS['confidence_consolidation'] is False
def test_schedule_and_maturity():
    assert m.CYCLES==40 and m.PRESENTATION_STEPS==20 and len(m.CYCLE_ORDER)==4
    assert m.MATURITY==350.0
def test_event_identity():
    r={'source':'L2E0','target':'PC4','target_compartment':'apical','scheduled_step':3,'arrival_step':4}
    assert m.event_key(r)==('L2E0','PC4','apical',3,4)
