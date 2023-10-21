import datetime
import os
import subprocess
import sys
import urllib.request
from functools import partial
from pathlib import Path
from typing import Tuple

import numpy as np
from tqdm import tqdm

from src.tools import listFD

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from src import aggregate_fields, _check_coords_range, _get_grib_projection, _get_threshold_value

# Pyproj engine
try:
    import pyproj

    PYPROJ_IMPORTED = True
except ImportError:
    PYPROJ_IMPORTED = False

# Pygrib engine
try:
    import pygrib

    PYGRIB_IMPORTED = True
except ImportError:
    PYGRIB_IMPORTED = False


class MissingOptionalDependency(Exception):
    """Raised when an optional dependency is needed but not found."""

    pass


def import_mrms_grib(filename, extent=None, window_size=1, **kwargs):
    """
    Importer for NSSL's Multi-Radar/Multi-Sensor System
    ([MRMS](https://www.nssl.noaa.gov/projects/mrms/)) rainrate product
    (grib format).

    The rainrate values are expressed in mm/h, and the dimensions of the data
    array are [latitude, longitude]. The first grid point (0,0) corresponds to
    the upper left corner of the domain, while (last i, last j) denote the
    lower right corner.

    Due to the large size of the dataset (3500 x 7000), a float32 type is used
    by default to reduce the memory footprint. However, be aware that when this
    array is passed to a pystep function, it may be converted to double
    precision, doubling the memory footprint.
    To change the precision of the data, use the *dtype* keyword.

    Also, by default, the original data is downscaled by 4
    (resulting in a ~4 km grid spacing).
    In case that the original grid spacing is needed, use `window_size=1`.
    But be aware that a single composite in double precipitation will
    require 186 Mb of memory.

    Finally, if desired, the precipitation data can be extracted over a
    sub region of the full domain using the `extent` keyword.
    By default, the entire domain is returned.

    Notes
    -----
    In the MRMS grib files, "-3" is used to represent "No Coverage" or
    "Missing data". However, in this reader replace those values by the value
    specified in the `fillna` argument (NaN by default).

    Note that "missing values" are not the same as "no precipitation" values.
    Missing values indicates regions with no valid measures.
    While zero precipitation indicates regions with valid measurements,
    but with no precipitation detected.

    Parameters
    ----------
    filename: str
        Name of the file to import.
    extent: None or array-like
        Longitude and latitude range (in degrees) of the data to be retrieved.
        (min_lon, max_lon, min_lat, max_lat).
        By default (None), the entire domain is retrieved.
        The extent can be in any form that can be converted to a flat array
        of 4 elements array (e.g., lists or tuples).
    window_size: array_like or int
        Array containing down-sampling integer factor along each axis.
        If an integer value is given, the same block shape is used for all the
        image dimensions.
        Default: window_size=4.

    {extra_kwargs_doc}

    Returns
    -------
    precipitation: 2D array, float32
        Precipitation field in mm/h. The dimensions are [latitude, longitude].
        The first grid point (0,0) corresponds to the upper left corner of the
        domain, while (last i, last j) denote the lower right corner.
    quality: None
        Not implement.
    metadata: dict
        Associated metadata (pixel sizes, map projections, etc.).
    """

    del kwargs

    if not PYGRIB_IMPORTED:
        raise MissingOptionalDependency(
            "pygrib package is required to import NCEP's MRMS products but it is not installed"
        )

    try:
        grib_file = pygrib.open(filename)
    except OSError:
        raise OSError(f"Error opening NCEP's MRMS file. " f"File Not Found: {filename}")

    if isinstance(window_size, int):
        window_size = (window_size, window_size)

    if extent is not None:
        extent = np.asarray(extent)
        if (extent.ndim != 1) or (extent.size != 4):
            raise ValueError(
                "The extent must be None or a flat array with 4 elements.\n"
                f"Received: extent.shape = {str(extent.shape)}"
            )

    # The MRMS grib file contain one message with the precipitation intensity
    grib_file.rewind()
    grib_msg = grib_file.read(1)[0]  # Read the only message

    # -------------------------
    # Read the grid information

    lr_lon = grib_msg["longitudeOfLastGridPointInDegrees"]
    lr_lat = grib_msg["latitudeOfLastGridPointInDegrees"]

    ul_lon = grib_msg["longitudeOfFirstGridPointInDegrees"]
    ul_lat = grib_msg["latitudeOfFirstGridPointInDegrees"]

    # Ni - Number of points along a latitude circle (west-east)
    # Nj - Number of points along a longitude meridian (south-north)
    # The lat/lon grid has a 0.01 degrees spacing.
    lats = np.linspace(ul_lat, lr_lat, grib_msg["Nj"])
    lons = np.linspace(ul_lon, lr_lon, grib_msg["Ni"])

    precip = grib_msg.values
    no_data_mask = precip == -3  # Missing values

    # Create a function with default arguments for aggregate_fields
    block_reduce = partial(aggregate_fields, method="mean", trim=True)

    if window_size != (1, 1):
        # Downscale data
        lats = block_reduce(lats, window_size[0])
        lons = block_reduce(lons, window_size[1])

        # Update the limits
        ul_lat, lr_lat = lats[0], lats[-1]  # Lat from North to south!
        ul_lon, lr_lon = lons[0], lons[-1]

        precip[no_data_mask] = 0  # block_reduce does not handle nan values
        precip = block_reduce(precip, window_size, axis=(0, 1))

        # Consider that if a single invalid observation is located in the block,
        # then mark that value as invalid.
        no_data_mask = block_reduce(
            no_data_mask.astype("int"), window_size, axis=(0, 1)
        ).astype(bool)

    lons, lats = np.meshgrid(lons, lats)
    precip[no_data_mask] = np.nan

    if extent is not None:
        # clip domain
        ul_lon, lr_lon = _check_coords_range(
            (extent[0], extent[1]), "longitude", (ul_lon, lr_lon)
        )

        lr_lat, ul_lat = _check_coords_range(
            (extent[2], extent[3]), "latitude", (ul_lat, lr_lat)
        )

        mask_lat = (lats >= lr_lat) & (lats <= ul_lat)
        mask_lon = (lons >= ul_lon) & (lons <= lr_lon)

        nlats = np.count_nonzero(mask_lat[:, 0])
        nlons = np.count_nonzero(mask_lon[0, :])

        precip = precip[mask_lon & mask_lat].reshape(nlats, nlons)

    proj_params = _get_grib_projection(grib_msg)
    pr = pyproj.Proj(proj_params)
    proj_def = " ".join([f"+{key}={value} " for key, value in proj_params.items()])

    xsize = grib_msg["iDirectionIncrementInDegrees"] * window_size[0]
    ysize = grib_msg["jDirectionIncrementInDegrees"] * window_size[1]

    x1, y1 = pr(ul_lon, lr_lat)
    x2, y2 = pr(lr_lon, ul_lat)

    metadata = dict(
        institution="NOAA National Severe Storms Laboratory",
        xpixelsize=xsize,
        ypixelsize=ysize,
        unit="mm/h",
        accutime=2.0,
        transform=None,
        zerovalue=0,
        projection=proj_def.strip(),
        yorigin="upper",
        threshold=_get_threshold_value(precip),
        x1=x1 - xsize / 2,
        x2=x2 + xsize / 2,
        y1=y1 - ysize / 2,
        y2=y2 + ysize / 2,
        cartesian_unit="degrees",
    )

    return precip, None, metadata

def utc_to_est(filename):
    to_datetime_ = datetime.datetime.strptime(filename[17:-9],"%Y%m%d-%H%S%f")
    to_datetime_ = to_datetime_-datetime.timedelta(hours=4)
    filename = filename[:17] + to_datetime_.strftime('%Y%m%d-%H%S%f')[:-4] + filename[-9:]
    return filename
import pandas
from datetime import date, timedelta
sdate = date(2021,7,1)   # start date
edate = date(2021,10,20)   # end date
dates = pandas.date_range(sdate,edate-timedelta(days=1),freq='d')
for _date in dates:
    print(_date, end='/r')
    url = f"https://mtarchive.geol.iastate.edu/2021/{'{:02d}'.format(_date.month)}/{'{:02d}'.format(_date.day)}/mrms/ncep/PrecipRate/"
    n_url = None
    save_path = '/home/eohl/Documents/projects/LINDA_Nowcasting'
    download_latest_mrms(url,n_url,save_path)

def download_latest_mrms(url, n_url, save_path, nb_observations=30):
    # Create folders if not existing
    Path(os.path.join(save_path, 'data')).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(save_path, 'img')).mkdir(parents=True, exist_ok=True)
    target = listFD(url)
    if n_url:
        n_target = listFD(n_url)
        target += n_target
    if not target:
        print('no files')
        quit()
    target = [e for e in target if e[-13:-11] in ['00', '10', '20', '30', '40', '50']]
    target.sort()
    files = target[:]
    for _file in tqdm(files, desc='Donwloading files...'):
        if _file.split('//')[-1] not in os.listdir(os.path.join(save_path, 'data')):
            urllib.request.urlretrieve(_file, os.path.join(save_path, 'data', _file.split('//')[-1]))
            # subprocess.check_call(["gunzip", '-f', os.path.join(save_path, 'data', utc_to_est(_file.split('//')[-1]))])


def load_latest_mrms(save_path, window_size=1, modified_shape : Tuple[tuple]  = None):
    files = {os.path.getmtime(os.path.join(save_path, 'data', f)): os.path.join(save_path, 'data', f) for f in
             os.listdir(os.path.join(save_path, 'data')) if
             os.path.isfile(os.path.join(save_path, 'data', f)) and f.endswith('grib2')}
    latest_timestep = list(files)
    latest_timestep.sort()
    _files = latest_timestep.copy()
    latest_timestep = latest_timestep[-1]
    latest_timestep = datetime.datetime.strptime(files[latest_timestep].split('/')[-1][-21:-6], "%Y%m%d-%H%M%S")
    R = {}
    for i, filetime in enumerate(tqdm(list(_files), desc='Loading MRMS data ...')):
        impo = import_mrms_grib(files[filetime], window_size=window_size)[0]
        if modified_shape:
            impo = impo[modified_shape[1][0]:modified_shape[1][1],modified_shape[0][0]:modified_shape[0][1]]
        R[i] = impo
    R = np.array(tuple([R[e] for e in list(R)]))
    precip = np.concatenate([precip_[None, :, :] for precip_ in R])

    return precip, latest_timestep
