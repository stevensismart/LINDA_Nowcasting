import numpy as np
from pysteps.motion.lucaskanade import dense_lucaskanade
from pysteps.verification import *
from pysteps import nowcasts

def sprog(self, R, V, n_leadtimes, n_cascade_levels, R_thr):
    """
    The S-PROG method described in :cite:`Seed2003`
    :param R: Array of shape (ar_order+1,m,n) containing the input precipitation fields ordered by timestamp from
    oldest to newest. The time steps between the inputs are assumed to be regular.
    :param V : motion field
    :param n_leadtimes: Steps to predict
    :param n_cascade_levels: The number of cascade levels to use.
    :param R_thr: The threshold value for minimum observable precipitation intensity.
    :return: Predicted
    """
    # Estimate the motion field
    # The S-PROG nowcast
    nowcast_method = nowcasts.get_method("sprog")
    advection = dense_lucaskanade(precip, verbose=True)

    R_f = nowcast_method(
        precip,
        advection,
        12,
        n_cascade_levels=24,
        R_thr=0.1,
    )
    return R_f

def test_ensemble_forecast(X_o, X_f):
    ensemble_skill(X_f,X_o,metric = "")
    probscores.CRPS(X_f, X_o)

from pysteps.verification.detcatscores import det_cat_fct
