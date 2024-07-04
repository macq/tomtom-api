import datetime as dt
from shapely import geometry as geo
import json
from typing import List, Literal, Optional, Union

import requests
from dataclass_wizard.errors import MissingFields
import geojson

from tomtom_api import config, log
from tomtom_api.traffic_stats.models.geospatial import TomtomNetwork, TomtomRoad
from tomtom_api.traffic_stats.models.jobs.area import TomtomAreaJob
from tomtom_api.traffic_stats.models.jobs.route import TomtomRouteJob
from tomtom_api.traffic_stats.models.jobs.traffic_density import TomtomTrafficDensityJob
from tomtom_api.traffic_stats.models.responses import (
    JsonIpResponse,
    TomtomErrorResponse,
    TomtomJobInfo,
    TomtomResponseAnalysis,
    TomtomResponseRouteFound,
    TomtomResponseSearchJobs,
    TomtomResponseStatus,
)
from tomtom_api.traffic_stats.models.status import TomtomJobState, TomtomReportType
from tomtom_api.traffic_stats.models.time import TomtomDateRange, TomtomTimeSet
from tomtom_api.utils.time import date_as_str

SubmittedTomtomJob = Union[
    int, TomtomResponseAnalysis, TomtomResponseStatus, TomtomJobInfo
]


class TomtomClient:
    key: str
    base_url: str
    version: int
    session: requests.Session

    def __init__(
        self,
        base_url: Optional[str] = None,
        version: Optional[int] = None,
        key: Optional[str] = None,
        proxy_ip: Optional[str] = None,
        proxy_port: Optional[int] = None,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
    ):
        self.key: str = key or config.api.key
        self.version: int = version or config.api.version
        self.base_url: str = base_url or config.api.base_url
        self.session = requests.Session()

        proxy_ip = proxy_ip or config.api.proxy.ip
        proxy_port = proxy_port or config.api.proxy.port
        proxy_username = proxy_username or config.api.proxy.username
        proxy_password = proxy_password or config.api.proxy.password

        tab = [
            proxy_ip is None,
            proxy_port is None,
            proxy_username is None,
            proxy_password is None,
        ]
        if not all([v == tab[0] for v in tab[1:]]):
            raise ValueError(
                "Some of the proxy information were given, but not all of them.\n"
                "Please check that you are defining all the proxy related variables."
            )

        self.proxy_url: Optional[str] = (
            None
            if proxy_ip is None
            else f"http://{proxy_username}:{proxy_password}@{proxy_ip}:{proxy_port}"
        )

        if self.key is None:
            raise ValueError("The client cannot be initialized without an API key.")
        if self.version is None:
            raise ValueError("The client cannot be initialized without a version.")
        if self.base_url is None:
            raise ValueError("The client cannot be initialized without a base url.")

    def __del__(self):
        try:
            self.session.close()
        except Exception:
            pass

    def request(self, *args, **kwargs) -> requests.Response:
        """Wrapper for requests.request method.
        This allows proxying the requests and perform common response validation.

        Returns
        -------
        requests.Response
            The response.

        Raises
        ------
        Exception
            If the user was not allowed to perform the query (403 Forbidden)
        """
        proxies = (
            None
            if self.proxy_url is None
            else {protocol: self.proxy_url for protocol in ["http", "https"]}
        )
        headers = {"content-type": "application/json"}
        r = self.session.request(
            *args, proxies=proxies, headers=headers, allow_redirects=True, **kwargs
        )
        log.debug(f"request: {r.text}")

        if r.status_code == 403:
            log.error(r.text)
            # todo: create custom exception for forbidden
            raise Exception(
                "The access is forbidden. Maybe you should check if the correct API key is loaded."
            )

        if r.status_code == 400:
            try:
                error = TomtomErrorResponse.from_dict(r.json())
                for message in error.messages:
                    log.error(
                        f"{message.error} ({message.field}):\n{message.rejected_value}"
                    )
            except MissingFields:
                error = TomtomResponseAnalysis.from_dict(r.json())
                for message in error.messages:
                    log.error(f"Job {error.job_id}: {message}")
                # since it can be converted as a TomtomResponseRouteAnalysis,
                # we can just return the original request.response
                return r

            raise Exception(
                "The given request generated an error (HTTP400). Please check logs for more info."
            )

        return r

    def route_analysis(
        self,
        job_name: str,
        distance_unit: Literal["KILOMETERS", "MILES"],
        roads: List[TomtomRoad],
        date_ranges: List[TomtomDateRange],
        time_sets: List[TomtomTimeSet],
        accept_mode: Optional[Literal["AUTO", "MANUAL"]] = "AUTO",
        map_version: Optional[float] = None,
        average_sample_size_threshold: Optional[int] = None,
    ) -> TomtomResponseAnalysis:
        """
        The Traffic Stats API Route Analysis service calculates the statistics for a defined route between an origin
        and a destination, optionally via waypoints. This service is asynchronous.

        Documentation: https://developer.tomtom.com/traffic-stats/documentation/api/route-analysis
        """
        job = TomtomRouteJob(
            job_name=job_name,
            distance_unit=distance_unit,
            routes=roads,
            date_ranges=date_ranges,
            time_sets=time_sets,
            accept_mode=accept_mode,
            map_version=map_version,
            average_sample_size_threshold=average_sample_size_threshold,
        )
        return self.post_job_route_analysis(job)

    def area_analysis(
        self,
        job_name: str,
        distance_unit: Literal["KILOMETERS", "MILES"],
        network: TomtomNetwork,
        date_range: TomtomDateRange,
        time_sets: List[TomtomTimeSet],
        accept_mode: Optional[Literal["AUTO", "MANUAL"]] = "AUTO",
        map_version: Optional[float] = None,
        average_sample_size_threshold: Optional[int] = None,
    ) -> TomtomResponseAnalysis:
        job = TomtomAreaJob(
            job_name=job_name,
            distance_unit=distance_unit,
            network=network,
            date_range=date_range,
            time_sets=time_sets,
            accept_mode=accept_mode,
            map_version=map_version,
            average_sample_size_threshold=average_sample_size_threshold,
        )
        return self.post_job_area_analysis(job)

    def traffic_density(
        self,
        job_name: str,
        distance_unit: Literal["KILOMETERS", "MILES"],
        network: TomtomNetwork,
        date_range: TomtomDateRange,
        time_sets: List[TomtomTimeSet],
        accept_mode: Optional[Literal["AUTO", "MANUAL"]] = "AUTO",
        map_version: Optional[float] = None,
        average_sample_size_threshold: Optional[int] = None,
    ) -> TomtomResponseAnalysis:
        job = TomtomTrafficDensityJob(
            job_name=job_name,
            distance_unit=distance_unit,
            network=network,
            date_range=date_range,
            time_sets=time_sets,
            accept_mode=accept_mode,
            map_version=map_version,
            average_sample_size_threshold=average_sample_size_threshold,
        )
        return self.post_job_traffic_density(job)

    def find_route(
        self,
        road: TomtomRoad,
        map_version: Optional[str] = None,
        map_type: Optional[str] = "DSEG_NOSPLIT",
    ) -> TomtomResponseRouteFound:
        """
        This API performs a check to see whether the road can be found with the given informations.

        Parameters
        ----------
        road : TomtomRoad
            The road to check
        map_version : Optional[str], optional
            The map version, by default '2016.12'
        map_type : Optional[str], optional
            Only two options are available, use 'OPEN_DSEG_NOSPLIT' for Japan, by default 'DSEG_NOSPLIT'

        Returns
        -------
        TomtomResponseRouteFound
            The response of the API.
        """
        url = f"https://{self.base_url}/traffic/trafficstats/route?key={self.key}"
        data = road.to_find_route_api_object(map_version, map_type)
        response = self.request("post", url, data=json.dumps(data))
        tomtom_response = TomtomResponseRouteFound.from_dict(response.json())
        return tomtom_response

    def post_job_route_analysis(self, job: TomtomRouteJob) -> TomtomResponseAnalysis:
        url = f"https://{self.base_url}/traffic/trafficstats/routeanalysis/{self.version}?key={self.key}"

        request_response = self.request("post", url, data=json.dumps(job.to_dict()))
        tomtom_response = TomtomResponseAnalysis.from_dict(request_response.json())
        return tomtom_response

    def post_job_area_analysis(self, job: TomtomAreaJob) -> TomtomResponseAnalysis:
        url = f"https://{self.base_url}/traffic/trafficstats/areaanalysis/{self.version}?key={self.key}"

        request_response = self.request("post", url, data=json.dumps(job.to_dict()))
        tomtom_response = TomtomResponseAnalysis.from_dict(request_response.json())
        return tomtom_response

    def post_job_traffic_density(
        self, job: TomtomTrafficDensityJob
    ) -> TomtomResponseAnalysis:
        url = f"https://{self.base_url}/traffic/trafficstats/trafficdensity/{self.version}?key={self.key}"

        request_response = self.request("post", url, data=json.dumps(job.to_dict()))
        tomtom_response = TomtomResponseAnalysis.from_dict(request_response.json())
        return tomtom_response

    def status(self, job_id: int) -> TomtomResponseStatus:
        """When a job has been initiated via the API request it is possible to check the status.

        Documentation:
            - https://developer.tomtom.com/traffic-stats/documentation/api/route-analysis#check-job-status
            - https://developer.tomtom.com/traffic-stats/documentation/api/area-analysis#check-job-status
            - https://developer.tomtom.com/traffic-stats/documentation/api/traffic-density#check-job-status

        Parameters
        ----------
        job_id: int
            The job id for which information is needed.

        Returns
        -------
        TomtomResponseStatus
            The requested information.
        """
        url = f"https://{self.base_url}/traffic/trafficstats/status/{self.version}/{job_id}?key={self.key}"

        request_response = self.request("get", url)
        tomtom_response = TomtomResponseStatus.from_dict(request_response.json())
        return tomtom_response

    def available_maps(
        self,
        geometry: Union[geo.Polygon, geo.MultiPolygon],
        start: dt.date,
        end: dt.date,
    ) -> List[str]:

        url = f"https://{self.base_url}/traffic/trafficstats/maps/{self.version}?key={self.key}"
        day_format = "%Y-%m-%d"
        data = {
            "geometry": geojson.Feature(geometry=geometry, properties={}).geometry,
            "dateRange": {
                "from": start.strftime(day_format),
                "to": end.strftime(day_format),
            },
        }
        request_response = self.request(
            "post",
            url,
            data=json.dumps(data),
        )

        if request_response.status_code == 400:
            messages = request_response.json()["messages"]
            message = "\n".join(messages)
            raise Exception(message)
        return request_response.json()["maps"]

    def search_jobs(
        self,
        page_index: Optional[int] = None,
        per_page: Optional[int] = None,
        created_after: Optional[Union[dt.date, str]] = None,
        created_before: Optional[Union[dt.date, str]] = None,
        completed_after: Optional[Union[dt.date, str]] = None,
        completed_before: Optional[Union[dt.date, str]] = None,
        name: Optional[str] = None,
        job_id: Optional[int] = None,
        job_type: Optional[Union[TomtomReportType, List[TomtomReportType]]] = None,
        state: Optional[Union[TomtomJobState, List[TomtomJobState]]] = None,
    ) -> TomtomResponseSearchJobs:
        """Fetch information about the jobs you have.
        You can either get them all or use some filters.

        Documentation: https://developer.tomtom.com/traffic-stats/documentation/api/search-jobs

        Parameters
        ----------
        page_index: Optional[int]
            Index of a page with jobs. Page counting starts from 0.
        per_page: Optional[int]
            Number of jobs included in the page. The last page may have less jobs.
        created_after: Optional[Union[dt.date, str]]
            Earliest date of requesting jobs (inclusive). [YYYY-MM-DD] Days change according to the UTC time zone.
        created_before: Optional[Union[dt.date, str]]
            Latest date of requesting jobs (inclusive). [YYYY-MM-DD] Days change according to the UTC time zone.
        completed_after: Optional[Union[dt.date, str]]
            Earliest date of completing jobs (inclusive). [YYYY-MM-DD] Days change according to the UTC time zone.
        completed_before: Optional[Union[dt.date, str]]
            Latest date of completing jobs (inclusive). [YYYY-MM-DD] Days change according to the UTC time zone.
        name: Optional[str]
            Name of job(s). By default exact match is done. % is a special character which allows for partial matching.
        job_id: Optional[int]
            Id of a job.
        job_type: Optional[Union[TomtomReportType, List[TomtomReportType]]]
            The type of jobs.
        state: Optional[TomtomJobState]
            The current state of jobs.

        Returns
        -------
        TomtomResponseSearchJob
            The response provided by the tomtom API
        """
        url = f"https://{self.base_url}/traffic/trafficstats/job/search/{self.version}?key={self.key}"

        if page_index is not None and page_index < 0:
            raise ValueError(
                f"page_index must be greater or equal to zero ({page_index} given)"
            )

        if per_page is not None and per_page <= 0:
            raise ValueError(f"per_page must be greater than zero ({per_page} given)")

        date_fmt = "%Y-%m-%d"

        # expand parameters that can be lists
        job_type = job_type if isinstance(job_type, list) else [job_type]
        job_type = [j for j in job_type if j is not None]
        state = state if isinstance(state, list) else [state]
        state = [s for s in state if s is not None]

        params = {
            "pageIndex": page_index,
            "perPage": per_page,
            "createdAfter": (
                None if created_after is None else date_as_str(created_after, date_fmt)
            ),
            "createdBefore": (
                None
                if created_before is None
                else date_as_str(created_before, date_fmt)
            ),
            "completedAfter": (
                None
                if completed_after is None
                else date_as_str(completed_after, date_fmt)
            ),
            "completedBefore": (
                None
                if completed_before is None
                else date_as_str(completed_before, date_fmt)
            ),
            "name": name,
            "id": job_id,
            "type": (
                None if len(job_type) < 1 else ",".join([j.value for j in job_type])
            ),
            "state": None if len(state) < 1 else ",".join([s.name for s in state]),
        }
        params = {k: v for k, v in params.items() if v is not None}

        request_response = self.request("get", url, params=params)
        return TomtomResponseSearchJobs.from_dict(request_response.json())

    def delete_job(self, job: Union[SubmittedTomtomJob, List[SubmittedTomtomJob]]):
        if isinstance(job, list):
            return [self.delete_job(elem) for elem in job]

        job_id = job if isinstance(job, int) else job.job_id

        url = f"https://{self.base_url}/traffic/trafficstats/reports/{job_id}/?key={self.key}"

        response = self.request("delete", url)

        return response

    def cancel_job(self, job: Union[SubmittedTomtomJob, List[SubmittedTomtomJob]]):
        if isinstance(job, list):
            return [self.cancel_job(elem) for elem in job]

        job_id = job if isinstance(job, int) else job.job_id

        url = f"https://{self.base_url}/traffic/trafficstats/status/{self.version}/{job_id}/cancel?key={self.key}"
        response = self.request("post", url)
        return response

    def check_ip(self, use_proxy: bool = False) -> JsonIpResponse:
        if use_proxy and self.proxy_url is None:
            raise Exception(
                "Trying to use a proxy while it is not configured.\n"
                "Try to setup the client with proxy values or look at your environment variables"
            )

        url = "https://jsonip.com/"

        # save the current self.proxy_url value
        tmp_proxy = self.proxy_url
        if not use_proxy:
            self.proxy_url = None

        # perform the query
        response = self.request("get", url)

        # do not forget to reset the self.proxy_url
        self.proxy_url = tmp_proxy

        # returning the response
        return JsonIpResponse.from_dict(response.json())


class DummyTomtomClient(TomtomClient):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

    def request(self, *args, **kwargs):
        raise Exception("This client is not meant to send requests.")

    def route_analysis(self, *args, **kwargs) -> TomtomResponseAnalysis:
        return TomtomResponseAnalysis("OK", ["This is a dummy response"], -1)

    def post_job_route_analysis(self, *args, **kwargs) -> TomtomResponseAnalysis:
        return TomtomResponseAnalysis(
            response_status="OK", messages=["This is a dummy response"], job_id=1
        )

    def post_job_area_analysis(self, *args, **kwargs) -> TomtomResponseAnalysis:
        return TomtomResponseAnalysis(
            response_status="OK", messages=["This is a dummy response"], job_id=1
        )

    def status(self, *args, **kwargs) -> TomtomResponseStatus:
        return TomtomResponseStatus(
            -1, TomtomJobState.DONE, "OK", ["https://google.be"]
        )

    def search_jobs(self, *args, **kwargs) -> TomtomResponseSearchJobs:
        from tomtom_api.traffic_stats.models.responses import (
            Pageable,
            Sort,
            TomtomJobInfo,
        )

        job_info = TomtomJobInfo(
            name="dummy job",
            created_at=dt.datetime.now(),
            state=TomtomJobState.DONE,
            job_id=1,
            completed_at=dt.datetime.now(),
            job_type="dummy",
        )
        sort = Sort(is_sorted=True, is_unsorted=False, is_empty=False)
        pageable = Pageable(
            sort=sort, page_size=1, page_number=1, offset=1, paged=True, unpaged=False
        )
        return TomtomResponseSearchJobs(
            content=[job_info],
            pageable=pageable,
            total_elements=1,
            last=True,
            total_pages=1,
            first=1,
            sort=sort,
            number_of_elements=1,
            size=1,
            number=1,
            empty=False,
        )

    def check_ip(self, *args, **kwargs) -> JsonIpResponse:
        raise Exception("This client is not meant to send requests.")
