from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from tomtom_api.traffic_stats import MAX_DATE_RANGE_COUNT, MAX_ROAD_COUNT
from tomtom_api.traffic_stats.models.geospatial import TomtomRoad
from tomtom_api.traffic_stats.models.jobs.base import TomtomJob
from tomtom_api.traffic_stats.models.time import TomtomDateRange, TomtomTimeSet


class TomtomRouteJob(TomtomJob):
    routes: List[TomtomRoad]

    def __init__(
        self,
        job_name: str,
        routes: List[TomtomRoad],
        date_ranges: List[TomtomDateRange],
        time_sets: List[TomtomTimeSet],
        distance_unit: Literal["KILOMETERS", "MILES"] = "KILOMETERS",
        accept_mode: Optional[Literal["AUTO", "MANUAL"]] = "AUTO",
        map_version: Optional[float] = None,
        average_sample_size_threshold: Optional[int] = None,
    ):
        """Data structure containing all the job information.

        Documentation: https://developer.tomtom.com/traffic-stats/documentation/api/route-analysis#request-post-body-parameters---json

        Parameters
        ----------
        job_name : str
            Job name which will be used in the process and output. Given for user's convenience
        routes : List[TomtomRoad]
            Roads for calculations. See `tomtom_api.traffic_stats.models.geospatial.TomtomRoad`.
        date_ranges : List[TomtomDateRange]
            Ranges of dates for calculations. See `tomtom_api.traffic_stats.models.time.TomtomDateRange`.
        time_sets : List[TomtomTimeSet]
            Time sets for calculations. See `tomtom_api.traffic_stats.models.time.TomtomTimeSet`.
        distance_unit : Literal['KILOMETERS', 'MILES'], optional
            Base unit for distance and speed values, by default 'KILOMETERS'
        accept_mode : Optional[Literal['AUTO', 'MANUAL']], optional
            Defines whether the job should be accepted manually or automatically, by default 'AUTO'
        map_version : Optional[float], optional
            What map should be used, by default 2020.09
        average_sample_size_threshold : Optional[int], optional
            If the average sample size for any combination of route, date range, and time set will be lower than
            the given value, then the output will not be generated, and the job will be moved into the REJECTED
            state and the user will not be charged for such a report.
            If not specified, the output will always be generated no matter how many samples were available.

        Raises
        ------
        ValueError
            If a conversion between types fails or if a limitation of the API is reached.
        """

        if len(routes) > MAX_ROAD_COUNT:
            raise ValueError(
                f"Impossible to query for more than {MAX_ROAD_COUNT} roads, ({len(routes)} given)"
            )
        self.routes = routes

        if len(date_ranges) > MAX_DATE_RANGE_COUNT:
            raise ValueError(
                f"Impossible to query for more than {MAX_DATE_RANGE_COUNT} date range, ({len(date_ranges)} given)"
            )
        self.date_ranges = date_ranges

        super().__init__(
            job_name=job_name,
            time_sets=time_sets,
            distance_unit=distance_unit,
            accept_mode=accept_mode,
            map_version=map_version,
            average_sample_size_threshold=average_sample_size_threshold,
        )

    @classmethod
    def from_dict(cls, dict_object: Dict[str, Any]) -> TomtomRouteJob:
        return cls(
            job_name=dict_object["jobName"],
            routes=[TomtomRoad.from_dict(r) for r in dict_object["routes"]],
            date_ranges=[
                TomtomDateRange.from_dict(d) for d in dict_object["dateRanges"]
            ],
            time_sets=[TomtomTimeSet.from_dict(t) for t in dict_object["timeSets"]],
            distance_unit=dict_object["distanceUnit"],
            accept_mode=dict_object["acceptMode"],
            map_version=dict_object["mapVersion"],
            average_sample_size_threshold=(
                None
                if "averageSampleSizeThreshold" not in dict_object
                else dict_object["averageSampleSizeThreshold"]
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Transform this data type to a python dictionary.
        This dict is meant to be used to generate the payload given to some Tomtom API endpoints.

        Returns
        -------
        Dict[str, float]
            The dictionary with the keys specified in the documentation.
        """
        job_dict = {
            **super().to_dict(),
            "dateRanges": [d.to_dict() for d in self.date_ranges],
            "routes": [r.to_dict() for r in self.routes],
        }

        return job_dict
