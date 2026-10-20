import numpy as np
import pytest
from lri_eh.finite_shell import compare

@pytest.mark.parametrize('lo,hi',[(4,8),(6,12)])
def test_against_dense_feshbach(lo,hi):
    from finite_shell_match import compare as dense
    ref=dense(lo,hi,7);new=compare(lo,hi,7,2.)
    for key in ('parent_C','matched_C','naive_low_same_parent_couplings_C'):
        np.testing.assert_allclose(new[key],ref[key],rtol=2e-11,atol=1e-7)
    assert new['max_parent_matched_energy_difference']<1e-7
