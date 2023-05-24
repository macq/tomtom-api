"""Responses models

In this module are grouped all the dataclasses that are hydrated when the API is responding something.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Type

import requests
from dataclass_wizard import JSONWizard, LoadMixin, json_field

from tomtom_api import log
from tomtom_api.traffic_stats.models.geospatial import TomtomPoint
from tomtom_api.utils.exceptions import DownloadException

from .status import TomtomDownloadFileType, TomtomJobState


@dataclass
class TomtomErrorResponseMessage(JSONWizard):
    error: str
    field: str
    rejected_value: str


@dataclass
class TomtomErrorResponse(JSONWizard):
    response_status: str
    messages: List[TomtomErrorResponseMessage]


@dataclass
class TomtomResponseAnalysis(JSONWizard):
    response_status: str
    messages: List[str]
    job_id: Optional[int] = None


@dataclass
class TomtomResponseStatus(JSONWizard, LoadMixin):
    job_id: int
    job_state: TomtomJobState
    response_status: str
    urls: Optional[List[str]]

    def __init__(self, job_id: int, job_state: TomtomJobState, response_status: str, urls: Optional[List[str]] = None):
        self.job_id = job_id
        self.job_state = job_state
        self.response_status = response_status
        self.urls = urls

    def load_to_enum(o, base_type: Type[Enum]) -> Enum:
        return base_type.from_str(o)

    def display_info(self) -> str:
        return f'{self.job_id} ({self.job_state.name})'

    def download(self, file_type: TomtomDownloadFileType) -> bytes:
        """Download the job report, in the given format.

        Parameters
        ----------
        file_type : TomtomDownloadFileType
            The wished file type.

        Returns
        -------
        bytes
            The content of the file, in bytes.

        Raises
        ------
        DownloadException
            If the job does not provide the following requirements:
                * the DONE status,
                * urls not None,
                * one and only one url that can be matched with the file type value (extension of the file)
            This exception can also be triggered if there is an error while downloading the file.
        """
        if self.job_state != TomtomJobState.DONE:
            raise DownloadException(f'The "DONE" state is required for downloading the report ({self.job_state}).')

        if self.urls is None:
            raise DownloadException('There is no download url for this job.')

        filtered_links = [link for link in self.urls if f'{file_type.value}?' in link]
        if len(filtered_links) != 1:
            log.debug(f'Available links: {self.urls}.')
            log.debug(f'Provided file type: {file_type}.')
            raise DownloadException(f'Impossible to find the desired file in the following links: {filtered_links}.')

        link = filtered_links[0]
        log.debug(f'Performing request to {link}')
        response = requests.get(link)

        if response.status_code != 200:
            log.debug(f'Response: {response}')
            raise DownloadException(f'Error while downloading {link}')

        return response.content

    def write(self, file: Path, file_type: TomtomDownloadFileType) -> None:
        """Download the job report and write it in a file.

        Parameters
        ----------
        file : Path
            The file path where the report should be stored
        file_type : TomtomDownloadFileType
            The wished file type.

        Examples
        --------
        >>> from tomtom_api.traffic_stats.client import TomtomClient
        >>> from tomtom_api.traffic_stats.models.status import TomtomDownloadFileType
        >>> from pathlib import Path
        >>> client = TomtomClient()
        >>> job_status = client.status(10)
        >>> job_status.write(Path('/tmp/myfile.xlsx'), TomtomDownloadFileType.EXCEL)
        """
        content = self.download(file_type)
        if file.exists():
            log.warning(f'The following file will be overwritten: {file}')

        log.debug(f'Writing file {file}')
        with open(file, 'wb') as f:
            f.write(content)


@dataclass
class TomtomResponseRouteFound(JSONWizard, LoadMixin):
    map_type: str
    map_version: str
    route_found: bool
    route: List[TomtomPoint]
    segments: List[str]


@dataclass
class TomtomJobInfo(JSONWizard, LoadMixin):
    name: str
    created_at: dt.datetime
    state: TomtomJobState
    job_id: int = json_field('id', all=True)
    job_type: str = json_field('type', all=True)
    completed_at: Optional[dt.datetime] = json_field('completed_at', default=None)

    def load_to_enum(o, base_type: Type[Enum]) -> Enum:
        return base_type.from_str(o)

    def display_info(self) -> str:
        datetime_fmt = '%Y-%m-%d %H:%M:%S'
        start = self.created_at.strftime(datetime_fmt)
        end = 'None' if self.completed_at is None else self.completed_at.strftime(datetime_fmt)
        return f'┌─ [{self.job_id}] {self.name} // {self.state.name}\n└─ {self.job_type} <{start} ⟶ {end}>'


@dataclass
class Sort(JSONWizard):
    is_sorted: bool = json_field('sorted', all=True)
    is_unsorted: bool = json_field('unsorted', all=True)
    is_empty: bool = json_field('empty', all=True)


@dataclass
class Pageable(JSONWizard):
    sort: Sort
    page_size: int
    page_number: int
    offset: int
    paged: bool
    unpaged: bool


@dataclass
class TomtomResponseSearchJobs(JSONWizard):
    content: List[TomtomJobInfo]
    pageable: Pageable
    total_elements: int
    last: bool
    total_pages: int
    first: bool
    sort: Sort
    number_of_elements: int
    size: int
    number: int
    empty: bool


@dataclass
class JsonIpResponse(JSONWizard):
    ip: str
    geo_ip: str = json_field('geo-ip', all=True)
    api_help: str = json_field('API Help', all=True)
