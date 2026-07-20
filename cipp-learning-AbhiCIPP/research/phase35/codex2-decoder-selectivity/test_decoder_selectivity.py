import importlib.util,sys
from pathlib import Path
P=Path(__file__).with_name('analyze_decoder_selectivity.py')
spec=importlib.util.spec_from_file_location('selectivity',P);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def test_categories():
    assert m.classify([])=='IMMATURE'
    assert m.classify([4])=='CENTER_ONLY'
    assert m.classify([3,4])=='PARTIAL_SINGLE_PATTERN'
    assert m.classify([3,4,5])=='COMPLETE_SINGLE_PATTERN'
    assert m.classify([1,3,4,5,7])=='MULTI_PATTERN_UNION'
    assert m.classify([1,3,4])=='SCATTERED_FRAGMENT'
def test_pattern_partition():
    assert len(m.PIXEL_PATTERNS[4])==4
    assert all(len(m.PIXEL_PATTERNS[i])==1 for i in range(9) if i!=4)
