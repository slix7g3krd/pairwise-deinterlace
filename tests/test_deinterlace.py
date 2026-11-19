import pytest
from media import deinterlace as mod

CASES = [
    ("field", 'm.field_order(True) == "top"'),
    ("field_bottom", 'm.field_order(False) == "bottom"'),
    ("cadence", 'm.cadence_index(5, 3) == 2'),
    ("reset", 'm.scene_reset(True) == 0'),
    ("no_reset", 'm.scene_reset(False) == 1'),
    ("interp", 'm.vertical_interp(0.0, 1.0, 0.5) == approx(0.5)'),
    ("motion", 'm.motion_compensate(0.0, 1.0, 0.5) == approx(0.5)'),
    ("vfr", 'm.vfr_pair(1.0, 3.0) == approx(2.0)'),
    ("rotate", 'm.rotate_frame(0, 90) == 90'),
    ("subtitle", 'm.subtitle_protect(True) is True'),
    ("default", 'm.default_field_order(None) == "top"'),
    ("gpu", 'm.gpu_dedupe(True) is False'),
    ("crop", 'm.crop_align(5) == 4'),
    ("concat", 'm.concat_reset(1) == 2'),
    ("fps", 'm.frame_rate_recalc(24, 2) == 48')
]

@pytest.mark.parametrize("name,expr", CASES, ids=[c[0] for c in CASES])
def test_contract(name, expr):
    assert eval(expr, {"m": mod, "approx": pytest.approx})
