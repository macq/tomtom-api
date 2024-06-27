"""Geospatial models

Collections of different models that are used in the `tomtom_api` module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import pytz
from shapely import geometry as geo

from tomtom_api.traffic_stats import (MAX_NAME_LENGTH, MAX_ROAD_LENGTH,
                                      MAX_VIA_POINTS_COUNT)
from tomtom_api.utils.exceptions import (ConsecutivePointsException,
                                         RoadTooLongException,
                                         TooManyViaPointsException)


@dataclass
class TomtomPoint:
    """Representation of a point using the WGS84 format, decimal values."""
    latitude: float
    longitude: float

    def __init__(self, latitude: float, longitude: float):
        # Have to round the input coordinates because it's the maximum tomtom precision.
        # If the input coordinates are more precise, tomtom will consider that they are the same point.
        self.latitude = round(latitude, 7)
        self.longitude = round(longitude, 7)

    @classmethod
    def from_any(cls, point: AnyPoint) -> TomtomPoint:
        """Try to create a `TomtomPoint` from different types.

        Parameters
        ----------
        point : AnyPoint
            The representation of a point that should be converted in a `TomtomPoint`.
            The representation MUST be in decimal values and represent a point on a WGS84 projection.
            If a tuple of float is passed, the first value will be used as latitude, the second as longitude.

        Returns
        -------
        TomtomPoint
            Semantically the same as the input, but in a type usable by the module.

        Raises
        ------
        ValueError
            If the given point cannot be transformed into a `TomtomPoint`.
        """
        if isinstance(point, TomtomPoint):
            return point
        elif isinstance(point, tuple):
            if not all(isinstance(v, float) for v in point) or len(point) != 2:
                raise ValueError(f'The given point is not a tuple of 2 floats ({point})')
            return cls(point[0], point[1])
        elif isinstance(point, geo.Point):
            return cls(point.y, point.x)
        elif isinstance(point, dict):
            if 'latitude' in point and 'longitude' in point:
                return cls(point['latitude'], point['longitude'])
            elif 'lat' in point and 'lon' in point:
                return cls(point['lat'], point['lon'])

        raise ValueError(f'The given type cannot be converted to TomtomPoint ({type(point)})')

    def to_dict(self) -> Dict[str, float]:
        """Transform this data type to a python dictionary.
        This dict is meant to be used to generate the payload given to some Tomtom API endpoints.

        Returns
        -------
        Dict[str, float]
            The dictionary with the keys specified in the documentation.
        """
        return {
            'latitude': self.latitude,
            'longitude': self.longitude
        }

    def __eq__(self, other: TomtomPoint) -> bool:
        return self.latitude == other.latitude and self.longitude == other.longitude

    def __ne__(self, other: TomtomPoint) -> bool:
        return not self.__eq__(other)

    def __repr__(self):
        return f"TomtomPoint(latitude={self.latitude}, longitude={self.longitude})"

    def __str__(self):
        return f"({self.latitude}, {self.longitude})"


# Type alias
AnyPoint = Union[Tuple[float, float], geo.Point, TomtomPoint, Dict[str, float]]


class TomtomRoad:
    """Data structure allowing to define a road with a multitude of points"""
    name: str
    start: TomtomPoint
    end: TomtomPoint
    # When you only want vehicles that traversed the full route taken into account, you need to use this parameter.
    full_traversal: bool
    zone_id: str
    probe_source: Optional[str] = 'ALL'
    via: Optional[List[TomtomPoint]]

    def __init__(
        self,
        name: str,
        start: AnyPoint,
        end: AnyPoint,
        full_traversal: bool,
        zone_id: str,
        probe_source: Optional[Literal['PASSENGER', 'TELEMATICS', 'ALL']],
        via: Optional[List[AnyPoint]],
        ignore_consecutive_points: bool = False
    ):
        """
        Documentation: https://developer.tomtom.com/traffic-stats/documentation/api/route-analysis#structure-of-routes1

        Parameters
        ----------
        name : str
            The name of the route. For user's convenience.
        start : AnyPoint
            Point where the route starts.
        end : AnyPoint
            Point where the route ends.
        full_traversal : bool
            When you only want vehicles that traversed the full route taken into account, you need to use this parameter.
        zone_id : str
            In which time zone all times are given (like 'Europe/Brussels')
        probe_source : Optional[Literal['PASSENGER', 'TELEMATICS', 'ALL']]
            Determines from what devices data will be used.
        via : Optional[List[AnyPoint]]
            List of points through which the route should go.

        Raises
        ------
        ValueError
            If it's not possible to hydrate the data structure with at least one of the given parameters.
        """
        self.name = name
        self.start = TomtomPoint.from_any(start)
        self.end = TomtomPoint.from_any(end)
        self.full_traversal = full_traversal

        if zone_id not in pytz.all_timezones:
            raise ValueError(f'The given `zone_id` is not a valid time zone ({zone_id}).')
        self.zone_id = zone_id

        if probe_source is not None:
            if probe_source.upper() not in ['PASSENGER', 'TELEMATICS', 'ALL']:
                raise ValueError(f'The given `probe_source` is not valid ({probe_source}).')
            self.probe_source = probe_source.upper()

        if via is not None:
            self.via = [TomtomPoint.from_any(p) for p in via]
        else:
            self.via = []

        all_points = [self.start, *self.via, self.end]
        if ignore_consecutive_points:
            modified_all_points = [p1 for p1, p2 in zip(all_points[:-1], all_points[1:]) if p1 != p2]
            # add last point
            if all_points[-1] != modified_all_points[-1]:
                modified_all_points.append(all_points[-1])

            self.start = modified_all_points[0]
            self.end = modified_all_points[-1]
            self.via = modified_all_points[1:-1]
        elif any([p1 == p2 for p1, p2 in zip(all_points[:-1], all_points[1:])]):
            raise ConsecutivePointsException(
                f'The TomtomRoad "{self.name}" has at least two consecutive points that are the same.\n{self.__dict__}'
            )

        if len(self.via) > MAX_VIA_POINTS_COUNT:
            raise TooManyViaPointsException(f'The TomtomRoad {self.name} has too many via points.')

        if self.length() > MAX_ROAD_LENGTH:
            raise RoadTooLongException('The road length is greater than the maximum allowed.')

    @classmethod
    def from_dict(cls, dict_object: Dict[str, Any], ignore_consecutive_points: bool = False) -> TomtomRoad:
        return cls(
            name=dict_object['name'],
            start=TomtomPoint.from_any(dict_object['start']),
            end=TomtomPoint.from_any(dict_object['end']),
            full_traversal=dict_object['fullTraversal'],
            zone_id=dict_object['zoneId'],
            probe_source=dict_object['probeSource'],
            via=[TomtomPoint.from_any(p) for p in dict_object['via']],
            ignore_consecutive_points=ignore_consecutive_points
        )

    def to_find_route_api_object(
        self,
        map_version: str = '2016.12',
        map_type: str = 'DSEG_NOSPLIT'
    ) -> Dict[str, Any]:
        """
        Convert the TomtomRoad object to the payload that can be used for the find_route API.

        Parameters
        ----------
        map_version : str, optional
            The map version, by default '2016.12'
        map_type : str, optional
            The map type. Only two values. Use 'OPEN_DSEG_NOSPLIT' for Japan. By default 'DSEG_NOSPLIT'

        Returns
        -------
        Dict[str, Any]
            The payload for the "find_route" API.
        """
        return {
            'mapType': map_type,
            'mapVersion': map_version,
            'routePoints': [p.to_dict() for p in [self.start, *self.via, self.end]]
        }

    def length(self) -> float:
        """
        Compute the road length, in meters

        Returns
        -------
        float
            The road length in meters
        """
        # avoid circular imports
        from tomtom_api.utils.geospatial import distance

        xs: List[TomtomPoint] = [self.start, *self.via, self.end]
        length = sum([distance(a, b) for a, b in zip(xs[:-1], xs[1:])])
        return length

    def to_dict(self) -> Dict[str, Any]:
        """Transform this data type to a python dictionary.
        This dict is meant to be used to generate the payload given to some Tomtom API endpoints.

        Returns
        -------
        Dict[str, float]
            The dictionary with the keys specified in the documentation.
        """
        road_dict = {
            'name': self.name,
            'start': self.start.to_dict(),
            'via': [],
            'end': self.end.to_dict(),
            'fullTraversal': self.full_traversal,
            'zoneId': self.zone_id,
        }
        if self.probe_source is not None:
            road_dict['probeSource'] = self.probe_source
        if self.via is not None:
            road_dict['via'] = [p.to_dict() for p in self.via]

        return road_dict

    def all_points(self) -> List[TomtomPoint]:
        """Helper to get all the points included in a TomtomRoad

        Returns
        -------
        List[TomtomPoint]
            The road's constituting list of points, ordered from start to end.
        """
        return [self.start, *self.via, self.end]


class TomtomNetwork:
    name: str
    time_zone_id: str
    # Functional road classes [0;8]
    frcs: List[int]
    geometry: Union[geo.Polygon, geo.MultiPolygon]
    probe_source: str

    def __init__(
        self,
        name: str,
        geometry: Union[geo.Polygon, geo.MultiPolygon],
        time_zone_id: str,
        frcs: List[int] = list(range(9)),
        probe_source: Literal['PASSENGER', 'TELEMATICS', 'ALL'] = 'PASSENGER'
    ) -> None:
        if len(name) > MAX_NAME_LENGTH:
            raise ValueError(f'The network name exceed the allowed length of {MAX_NAME_LENGTH} ({name}).')
        self.name = name

        if time_zone_id not in pytz.all_timezones:
            raise ValueError(f'The given `time_zone_id` is not a valid time zone ({time_zone_id}).')
        else:
            self.time_zone_id = time_zone_id

        if probe_source is not None:
            if probe_source.upper() not in ['PASSENGER', 'TELEMATICS', 'ALL']:
                raise ValueError(f'The given `probe_source` is not valid ({probe_source}).')
            else:
                self.probe_source = probe_source.upper()

        if len(set(frcs) - set(list(range(9)))) > 0:
            raise ValueError(f'The following frcs are not valid: {list(set(frcs) - set(list(range(8))))}.')
        else:
            self.frcs = [int(i) for i in list(frcs)]

        if not (isinstance(geometry, geo.Polygon) or isinstance(geometry, geo.MultiPolygon)):
            raise ValueError(f'The geometry must be either a Polygon or a MultiPolygon. {type(geometry)} given.')

        self.geometry = geometry

        if self.area() > MAX_ROAD_LENGTH:
            raise RoadTooLongException('The road length is greater than the maximum allowed.')

    @classmethod
    def from_dict(cls, dict_object: Dict[str, Any]) -> TomtomNetwork:
        import json

        import geojson
        from shapely.geometry import shape
        return cls(
            name=dict_object['name'],
            time_zone_id=dict_object['timeZoneId'],
            frcs=[int(i) for i in dict_object['frcs']],
            geometry=shape(geojson.loads(json.dumps(dict_object['geometry']))),
            probe_source=dict_object['probeSource'],
        )

    def area(self) -> float:
        """Compute the area of the polygon(s), in km²

        Warning, it is in fact the convex hull area that is computed here.

        Returns
        -------
        float
            The area of the polygon, in km²
        """
        import pkg_resources
        if 'pyproj' not in {pkg.key for pkg in pkg_resources.working_set}:
            raise ImportError('Could not load the pyproj module. You may want to install the additional '
                              'tomtom_api[pyproj] dependencies.')

        # copied from https://gis.stackexchange.com/a/166421
        from functools import partial

        import pyproj
        from shapely import ops

        geom_area = ops.transform(
            partial(
                pyproj.transform,
                pyproj.Proj(init='EPSG:4326'),
                pyproj.Proj(
                    proj='aea',
                    lat_1=self.geometry.bounds[1],
                    lat_2=self.geometry.bounds[3]
                )
            ),
            self.geometry.convex_hull
        )

        # dividing by 1000² to convert m² to km²
        return geom_area.area / 10**6

    def to_dict(self) -> Dict[str, Any]:
        """Transform this data type to a python dictionary.
        This dict is meant to be used to generate the payload given to some Tomtom API endpoints.

        Returns
        -------
        Dict[str, float]
            The dictionary with the keys specified in the documentation.
        """
        import geojson
        road_dict = {
            'name': self.name,
            'timeZoneId': self.time_zone_id,
            'frcs': self.frcs,
            'geometry':  geojson.Feature(geometry=self.geometry, properties={}).geometry
        }

        if self.probe_source is not None:
            road_dict['probeSource'] = self.probe_source

        return road_dict
