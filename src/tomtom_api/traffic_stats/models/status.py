from __future__ import annotations

from enum import Enum


class TomtomReportType(Enum):
    ROUTE_ANALYSIS = 'routeanalysis'
    AREA_ANALYSIS = 'areaanalysis'
    TRAFFIC_DENSITY = 'trafficdensity'


class TomtomJobState(Enum):
    """Job status
    During the process there are different stages applicable. Via the get state request you can see what the state of
    your job is.

    Documentation: https://developer.tomtom.com/traffic-stats/documentation/api/route-analysis#job-status-flow
    """
    NEW = 0                 # The job is waiting for mapmatching to start.
    SCHEDULED = 1           # Job is scheduled for calculations.
    MAPMATCHING = 2         # Mapmatching is in progress.
    MAPMATCHED = 3          # Mapmatching is done and the job is waiting for Geobase reading.
    READING_GEOBASE = 4     # Geobase reading is in progress.
    CALCULATIONS = 5        # Calculations are in progress.
    NEED_CONFIRMATION = 6   # Occurs only if manual acceptance mode was used. See documentation link.
    DONE = 7                # Calculations are done. The results are waiting to be downloaded.
    ERROR = 8               # The job stopped due to the fact that something went wrong.
    REJECTED = 9            # The job is rejected. See documentation link.
    CANCELED = 10           # The job is cancelled. The owner of the job stopped processing it.
    EXPIRED = 11            # The job is older than a year and all data has been removed.

    @classmethod
    def from_str(cls, status: str) -> TomtomJobState:
        """Convert a string into a `TomtomJobState`.

        Parameters
        ----------
        status : str
            The status that needs to be converted. This status have to match one of the Enum's names.

        Returns
        -------
        TomtomJobState
            One of the state of this type.

        Raises
        ------
        ValueError
            If the given status was not in the list.
        """
        status = status.upper()
        tomtom_status = list(filter(
            lambda s: status == str(s).replace(f'{cls.__name__}.', ''),
            [s for s in TomtomJobState]
        ))
        if len(tomtom_status) != 1:
            raise ValueError(f'The given status is invalid ({status})')
        return tomtom_status[0]


class TomtomDownloadFileType(Enum):
    GEOJSON = '.geojson.zip'
    JSON = '.json'
    KMZ = '.kmz'
    SHAPEFILE = '.shapefile.zip'
    EXCEL = '.xlsx'
