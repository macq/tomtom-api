from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from tomtom_api.traffic_stats.models.geospatial import TomtomNetwork
from tomtom_api.traffic_stats.models.jobs.base import TomtomJob
from tomtom_api.traffic_stats.models.time import TomtomDateRange, TomtomTimeSet


class TomtomTrafficDensityJob(TomtomJob):
    network: TomtomNetwork

    def __init__(
        self,
        job_name: str,
        network: TomtomNetwork,
        date_range: TomtomDateRange,
        time_sets: List[TomtomTimeSet],
        distance_unit: Literal['KILOMETERS', 'MILES'] = 'KILOMETERS',
        accept_mode: Optional[Literal['AUTO', 'MANUAL']] = 'AUTO',
        map_version: Optional[float] = None,
        average_sample_size_threshold: Optional[int] = None
    ):
        self.network = network
        self.date_range = date_range
        super().__init__(job_name, time_sets, distance_unit, accept_mode, map_version, average_sample_size_threshold)

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
            'dateRange': self.date_range.to_dict(),
            'network': self.network.to_dict()
        }

        return job_dict

    @classmethod
    def from_dict(cls, dict_object: Dict[str, Any]) -> TomtomTrafficDensityJob:
        return cls(
            job_name=dict_object['jobName'],
            network=TomtomNetwork.from_dict(dict_object['network']),
            date_range=TomtomDateRange.from_dict(dict_object['dateRange']),
            time_sets=[TomtomTimeSet.from_dict(t) for t in dict_object['timeSets']],
            distance_unit=dict_object['distanceUnit'],
            accept_mode=dict_object['acceptMode'],
            map_version=dict_object['mapVersion'],
            average_sample_size_threshold=None if 'averageSampleSizeThreshold' not in dict_object else dict_object[
                'averageSampleSizeThreshold']
        )
