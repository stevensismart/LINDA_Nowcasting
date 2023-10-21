import numpy as np

_aggregation_methods = dict(
    sum=np.sum, mean=np.mean, nanmean=np.nanmean, nansum=np.nansum
)



def _get_threshold_value(precip):
    """
    Get the the rain/no rain threshold with the same unit, transformation and
    accutime of the data.
    If all the values are NaNs, the returned value is `np.nan`.
    Otherwise, np.min(precip[precip > precip.min()]) is returned.

    Returns
    -------
    threshold: float
    """
    valid_mask = np.isfinite(precip)
    if valid_mask.any():
        _precip = precip[valid_mask]
        min_precip = _precip.min()
        above_min_mask = _precip > min_precip
        if above_min_mask.any():
            return np.min(_precip[above_min_mask])
        else:
            return min_precip
    else:
        return np.nan

def aggregate_fields(data, window_size, axis=0, method="mean", trim=False):
    """Aggregate fields along a given direction.

    It attempts to aggregate the given R axis in an integer number of sections
    of length = ``window_size``.
    If such a aggregation is not possible, an error is raised unless ``trim``
    set to True, in which case the axis is trimmed (from the end)
    to make it perfectly divisible".

    Parameters
    ----------
    data: array-like
        Array of any shape containing the input fields.
    window_size: int or tuple of ints
        The length of the window that is used to aggregate the fields.
        If a single integer value is given, the same window is used for
        all the selected axis.

        If ``window_size`` is a 1D array-like,
        each element indicates the length of the window that is used
        to aggregate the fields along each axis. In this case,
        the number of elements of 'window_size' must be the same as the elements
        in the ``axis`` argument.
    axis: int or array-like of ints
        Axis or axes where to perform the aggregation.
        If this is a tuple of ints, the aggregation is performed over multiple
        axes, instead of a single axis
    method: string, optional
        Optional argument that specifies the operation to use
        to aggregate the values within the window.
        Default to mean operator.
    trim: bool
         In case that the ``data`` is not perfectly divisible by
         ``window_size`` along the selected axis:

         - trim=True: the data will be trimmed (from the end) along that
           axis to make it perfectly divisible.
         - trim=False: a ValueError exception is raised.

    Returns
    -------
    new_array: array-like
        The new aggregated array with shape[axis] = k,
        where k = R.shape[axis] / window_size.

    See also
    --------
    pysteps.utils.dimension.aggregate_fields_time,
    pysteps.utils.dimension.aggregate_fields_space
    """

    if np.ndim(axis) > 1:
        raise TypeError(
            "Only integers or integer 1D arrays can be used for the " "'axis' argument."
        )

    if np.ndim(axis) == 1:
        axis = np.asarray(axis)
        if np.ndim(window_size) == 0:
            window_size = (window_size,) * axis.size

        window_size = np.asarray(window_size, dtype="int")

        if window_size.shape != axis.shape:
            raise ValueError(
                "The 'window_size' and 'axis' shapes are incompatible."
                f"window_size.shape: {str(window_size.shape)}, "
                f"axis.shape: {str(axis.shape)}, "
            )

        new_data = data.copy()
        for i in range(axis.size):
            # Recursively call the aggregate_fields function
            new_data = aggregate_fields(
                new_data, window_size[i], axis=axis[i], method=method, trim=trim
            )

        return new_data

    if np.ndim(window_size) != 0:
        raise TypeError(
            "A single axis was selected for the aggregation but several"
            f"of window_sizes were given: {str(window_size)}."
        )

    data = np.asarray(data).copy()
    orig_shape = data.shape

    if method not in _aggregation_methods:
        raise ValueError(
            "Aggregation method not recognized. "
            f"Available methods: {str(list(_aggregation_methods.keys()))}"
        )

    if window_size <= 0:
        raise ValueError("'window_size' must be strictly positive")

    if (orig_shape[axis] % window_size) and (not trim):
        raise ValueError(
            f"Since 'trim' argument was set to False,"
            f"the 'window_size' {window_size} must exactly divide"
            f"the dimension along the selected axis:"
            f"data.shape[axis]={orig_shape[axis]}"
        )

    new_data = data.swapaxes(axis, 0)
    if trim:
        trim_size = data.shape[axis] % window_size
        if trim_size > 0:
            new_data = new_data[:-trim_size]

    new_data_shape = list(new_data.shape)
    new_data_shape[0] //= window_size  # Final shape

    new_data = new_data.reshape(new_data_shape[0], window_size, -1)

    new_data = _aggregation_methods[method](new_data, axis=1)

    new_data = new_data.reshape(new_data_shape).swapaxes(axis, 0)

    return new_data