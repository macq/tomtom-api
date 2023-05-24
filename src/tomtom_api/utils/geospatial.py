"""Utility functions grouped by theme: geospatial"""
import pkg_resources
from tomtom_api.traffic_stats.models.geospatial import TomtomPoint


def distance(a: TomtomPoint, b: TomtomPoint) -> float:
    """Compute the distance between two points.
    We are sure (because of tomtom specifications) that those points are expressed in EPSG4326 / WGS84

    Parameters
    ----------
    a : TomtomPoint
        The departure point
    b : TomtomPoint
        The arrival point

    Returns
    -------
    float
        The distance in meters
    """
    if 'pyproj' in {pkg.key for pkg in pkg_resources.working_set}:
        from pyproj import Geod
        g = Geod(ellps='WGS84')
        _, _, dist = g.inv(a.longitude, a.latitude, b.longitude, b.latitude)
        return dist
    else:
        return haversine(a.longitude, a.latitude, b.longitude, b.latitude)


def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Calculate the great circle distance in meters between two points
    on the earth (specified in decimal degrees)

    Parameters
    ----------
    lon1: float
        The longitude of the first point.
    lat1: float
        The latitude of the first point.
    lon2: float
        The longitude of the second point.
    lat2: float
        The latitude of the seconde point.

    Returns
    -------
    float
        The distance between those two points, in meter
    """
    from math import asin, cos, radians, sin, sqrt

    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    d_lon = lon2 - lon1
    d_lat = lat2 - lat1
    a = sin(d_lat/2)**2 + cos(lat1) * cos(lat2) * sin(d_lon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371000  # Radius of earth in meters. Use 3956 for miles. Determines return value units.
    return c * r
