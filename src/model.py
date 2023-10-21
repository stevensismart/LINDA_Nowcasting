from pysteps.motion.lucaskanade import dense_lucaskanade
from pysteps.nowcasts import linda
from pysteps.postprocessing import ensemblestats
import numpy as np
import multiprocessing


def nowcast(R, nb_forecasts = 12,threshold = 1):
    # Replace precipitation negative and none by zero
    R[np.isnan(R)] = 0
    R[R < 0] = 0
    # Pool initiation
    pool = multiprocessing.Pool()
    # The advection field is estimated using the Lucas-Kanade optical flow
    advection = dense_lucaskanade(R, verbose=True)
    # Compute 30-minute LINDA nowcast ensemble with 40 members and 8 parallel workers
    nowcast_linda = linda.forecast(
        precip_fields = R,
        advection_field = advection,
        timesteps = nb_forecasts,
        max_num_features=25,
        feature_method="domain",
        add_perturbations=True,
        num_ens_members=12,
        num_workers=pool._processes,
        measure_time=True,
        ari_order=2,
        kernel_type="anisotropic",
        extrap_method="semilagrangian",
        use_multiprocessing=True,
    )[0]

    excedance = ensemblestats.excprob(nowcast_linda, threshold)
    print('#### Finished Nowcasting ####')
    return excedance, nowcast_linda
