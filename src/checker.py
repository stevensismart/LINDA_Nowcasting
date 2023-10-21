def _check_coords_range(selected_range, coordinate, full_range):
    """Check that the coordinates range arguments follow the expected pattern in
    the **import_mrms_grib** function."""

    if selected_range is None:
        return sorted(full_range)

    if not isinstance(selected_range, (list, tuple)):

        if len(selected_range) != 2:
            raise ValueError(
                f"The {coordinate} range must be None or a two-element tuple or list"
            )

        selected_range = list(selected_range)  # Make mutable

        for i in range(2):
            if selected_range[i] is None:
                selected_range[i] = full_range

        selected_range.sort()

    return tuple(selected_range)



def _get_grib_projection(grib_msg):
    """Get the projection parameters from the grib file."""
    projparams = grib_msg.projparams

    # Some versions of pygrib defines the regular lat/lon projections as "cyl",
    # which causes errors in pyproj and cartopy. Here we replace it for "longlat".
    if projparams["proj"] == "cyl":
        projparams["proj"] = "longlat"

    # Grib C tables (3-2)
    # https://apps.ecmwf.int/codes/grib/format/grib2/ctables/3/2
    # https://en.wikibooks.org/wiki/PROJ.4
    _grib_shapes_of_earth = dict()
    _grib_shapes_of_earth[0] = {"R": 6367470}
    _grib_shapes_of_earth[1] = {"R": 6367470}
    _grib_shapes_of_earth[2] = {"ellps": "IAU76"}
    _grib_shapes_of_earth[4] = {"ellps": "GRS80"}
    _grib_shapes_of_earth[5] = {"ellps": "WGS84"}
    _grib_shapes_of_earth[6] = {"R": 6371229}
    _grib_shapes_of_earth[8] = {"datum": "WGS84", "R": 6371200}
    _grib_shapes_of_earth[9] = {"datum": "OSGB36"}

    # pygrib defines the ellipsoids using "a" and "b" only.
    # Here we replace the for the PROJ.4 SpheroidCodes if they are available.
    if grib_msg["shapeOfTheEarth"] in _grib_shapes_of_earth:
        keys_to_remove = ["a", "b"]
        for key in keys_to_remove:
            if key in projparams:
                del projparams[key]

        projparams.update(_grib_shapes_of_earth[grib_msg["shapeOfTheEarth"]])

    return projparams