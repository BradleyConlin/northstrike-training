import numpy as np

from src.estimators.ekf_cv import EKFCV


def test_shapes_and_stability():
    ekf = EKFCV()
    st = ekf.init(0.0, 0.0, 0.0)
    assert st.x.shape == (6, 1) and st.P.shape == (6, 6)
    st = ekf.predict(st, 0.1)
    st = ekf.update_pos(st, 0.0, 0.0, 0.0)
    # diagonals positive, finite
    assert np.all(np.isfinite(st.x))
    assert np.all(np.diag(st.P) > 0)
