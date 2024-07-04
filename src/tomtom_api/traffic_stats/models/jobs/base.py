from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional

from tomtom_api.traffic_stats import MAX_TIME_SETS_COUNT
from tomtom_api.traffic_stats.models.time import TomtomDateRange, TomtomTimeSet


class TomtomJob:
    """Data structure allowing the manipulation of the tomtom jobs"""

    job_name: str
    date_ranges: List[TomtomDateRange]
    time_sets: List[TomtomTimeSet]
    distance_unit: str = "KILOMETERS"
    accept_mode: Optional[str] = "AUTO"
    # see here for more info about map versions
    # https://developer.tomtom.com/traffic-stats/documentation/api/available-maps
    map_version: Optional[float] = None
    average_sample_size_threshold: Optional[int] = None

    def __init__(
        self,
        job_name: str,
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
        self.job_name = job_name

        if len(time_sets) > MAX_TIME_SETS_COUNT:
            raise ValueError(
                f"Impossible to query for more than {MAX_TIME_SETS_COUNT} time sets, ({len(time_sets)} given)"
            )
        self.time_sets = time_sets

        if distance_unit.upper() not in ["KILOMETERS", "MILES"]:
            raise ValueError(f"The given `distance_unit` is invalid ({distance_unit})")
        self.distance_unit = str(distance_unit).upper()

        if accept_mode is not None and accept_mode.upper() not in ["AUTO", "MANUAL"]:
            raise ValueError(f"The given `accept_mode` is invalid ({accept_mode})")
        self.accept_mode = accept_mode

        self.map_version = map_version
        self.average_sample_size_threshold = average_sample_size_threshold

    @classmethod
    def from_dict(cls, dict_object: Dict[str, Any]) -> TomtomJob:
        return cls(
            job_name=dict_object["jobName"],
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

    def md5(self, salt: str = "") -> str:
        import hashlib

        json = self.to_json()
        md5_hash = hashlib.md5(f"{json}{salt}".encode("utf-8"))
        return md5_hash.hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Transform this data type to a python dictionary.
        This dict is meant to be used to generate the payload given to some Tomtom API endpoints.

        Returns
        -------
        Dict[str, float]
            The dictionary with the keys specified in the documentation.
        """
        job_dict = {
            "jobName": self.job_name,
            "distanceUnit": self.distance_unit,
            "mapVersion": None,
            "acceptMode": None,
            "timeSets": [t.to_dict() for t in self.time_sets],
            "averageSampleSizeThreshold": None,
        }

        # manage optional fields
        if self.accept_mode is not None:
            job_dict["acceptMode"] = self.accept_mode
        if self.map_version is not None:
            job_dict["mapVersion"] = self.map_version
        if self.average_sample_size_threshold is not None:
            job_dict["averageSampleSizeThreshold"] = self.average_sample_size_threshold

        job_dict = {k: v for k, v in job_dict.items() if v is not None}

        return job_dict

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
