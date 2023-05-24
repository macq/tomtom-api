from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Optional

import pandas as pd

from tomtom_api import config, log
from tomtom_api.client import TomtomClient
from tomtom_api.priority_queue.models.status import QueueItemStatus
from tomtom_api.traffic_stats.models.jobs.area import TomtomAreaJob
from tomtom_api.traffic_stats.models.jobs.base import TomtomJob
from tomtom_api.traffic_stats.models.jobs.route import TomtomRouteJob
from tomtom_api.traffic_stats.models.status import TomtomJobState


class QueueItem:
    uid: str
    name: str
    report_type: str
    payload: TomtomJob
    priority: int
    created_timestamp: dt.datetime
    updated_timestamp: Optional[dt.datetime]
    submitted_timestamp: Optional[dt.datetime]
    completed_timestamp: Optional[dt.datetime]
    cancelled_timestamp: Optional[dt.datetime]
    tomtom_job_id: Optional[int]
    payload_link: Path

    def __init__(
        self,
        name: str,
        payload: TomtomRouteJob,
        priority: int = 5,
        created_timestamp: dt.datetime = dt.datetime.now().astimezone(),
        uid: str = None,
        report_type: Optional[str] = None,
        updated_timestamp: Optional[dt.datetime] = None,
        submitted_timestamp: Optional[dt.datetime] = None,
        completed_timestamp: Optional[dt.datetime] = None,
        cancelled_timestamp: Optional[dt.datetime] = None,
        error_timestamp: Optional[dt.datetime] = None,
        tomtom_job_id: Optional[int] = None
    ) -> None:
        self.uid = uid or payload.md5(name)
        self.name = name
        self.report_type = report_type if payload is None else payload.__class__.__name__
        self.payload = payload
        self.priority = priority
        self.created_timestamp = created_timestamp
        self.updated_timestamp = updated_timestamp
        self.submitted_timestamp = submitted_timestamp
        self.completed_timestamp = completed_timestamp
        self.cancelled_timestamp = cancelled_timestamp
        self.error_timestamp = error_timestamp
        self.tomtom_job_id = None if pd.isna(tomtom_job_id) else int(tomtom_job_id)
        self.payload_link = config.path.home / 'payloads' / f'{self.uid}.json'
        if not self.payload_link.exists():
            self.store_payload()

    @classmethod
    def new(cls, name: str, payload: TomtomJob, priority: int = 5) -> QueueItem:
        return cls(name, payload, priority)

    @classmethod
    def from_dict(cls, payload_link: Path, report_type: str, **kwargs) -> QueueItem:
        if report_type == 'TomtomRouteJob':
            report_class = TomtomRouteJob
        elif report_type == 'TomtomAreaJob':
            report_class = TomtomAreaJob
        else:
            raise ValueError(f'Unknown report type "{report_type}".')

        try:
            f = open(payload_link, 'r')
            payload = report_class.from_dict(json.load(f))
        except FileNotFoundError:
            payload = None

        return cls(payload=payload, report_type=report_type, **kwargs)

    def store_payload(self) -> None:
        """Write the TomtomJob of this queued item to a file.

        To avoid storing the payload in the database, we store the payload to a file and save that file location
        to the database.

        This method is responsible for storing the payload to a given location as JSON.
        """
        if self.get_status() in [QueueItemStatus.COMPLETED, QueueItemStatus.HAS_ERROR]:
            # log(5, message) will print the message only for a custom log_level that is below DEBUG (debug=10)
            log.log(5, f'Not storing the payload of a completed/erroneous job ({self.uid}).')
            return None

        if self.payload is None:
            self.error(f'The job {self.uid} had a None payload.')
            return None

        log.debug(f'Storing payload in {self.payload_link}')
        self.erase()
        self.payload_link.parent.mkdir(parents=True, exist_ok=True)
        with open(self.payload_link, 'w') as f:
            json.dump(self.payload.to_dict(), f)

    def erase(self) -> None:
        """Remove the payload file"""
        self.payload_link.unlink(missing_ok=True)

    def update(
        self,
        name: Optional[str] = None,
        priority: Optional[int] = None,
        cancel: Optional[bool] = None,
        payload: Optional[TomtomJob] = None,
    ) -> None:
        """Update this object with the given new values.

        Parameters
        ----------
        name : Optional[str], optional
            The new name of the queued item, by default None
        priority : Optional[int], optional
            The new priority of the queued item, by default None
        cancel : Optional[bool], optional
            Wether or not the job shouldn't be submitted to tomtom API. True to cancel the submission, False to remove
            the cancellation, by default None
        payload : Optional[TomtomJob], optional
            The new payload for this queued item, by default None

        Raises
        ------
        ValueError
            If no parameter is provided.
        """
        log.debug(f'Updating job {self.uid}')
        if self.get_status() in [QueueItemStatus.COMPLETED, QueueItemStatus.HAS_ERROR, QueueItemStatus.SUBMITTED]:
            raise ValueError(f'Cannot update the queued item because it has the status {self.get_status()}.')

        if all([e is None for e in [name, priority, payload, cancel]]):
            raise ValueError('At least one attribute should be updated. Otherwise just do not call the update method!')

        self.updated_timestamp = dt.datetime.now().astimezone()

        if name is not None:
            self.name = name

        if priority is not None:
            self.priority = priority

        if payload is not None:
            self.payload = payload
            self.store_payload()

        if cancel is not None:
            if cancel:
                self.cancel()
            else:
                self.cancelled_timestamp = None

    def error(self, message: Optional[str] = None) -> None:
        """Trigger the error status

        Parameters
        ----------
        message: Optional[str]
            Additional information to be displayed in the logs.
        """
        log.warning(f'Error generated for job {self.uid}.')
        if message is not None:
            log.error(message)
        self.error_timestamp = dt.datetime.now().astimezone()

    def submit(self, client: TomtomClient) -> None:
        """Trigger the submitted status

        This method is responsible for the submission of this queued item to the Tomtom API.

        Parameters
        ----------
        client : TomtomClient
            The TomtomClient that will perform the submission

        Raises
        ------
        ValueError
            if this item status is not waiting.
        """
        log.debug(f'Submitting job {self.uid}')
        if self.get_status() != QueueItemStatus.IS_WAITING:
            raise ValueError(
                f'To be submitted, the status of job {self.uid} should be WAITING, not {self.get_status()}.')

        if self.payload is None:
            raise ValueError('The payload can\'t be None for submitting the job!')

        if isinstance(self.payload, TomtomRouteJob):
            tomtom_api = client.post_job_route_analysis
        elif isinstance(self.payload, TomtomAreaJob):
            tomtom_api = client.post_job_area_analysis
        else:
            raise ValueError(f'The report type is not valid ({self.report_type}).')

        self.submitted_timestamp = dt.datetime.now().astimezone()

        response = tomtom_api(job=self.payload)
        self.tomtom_job_id = response.job_id
        if response.response_status.lower() == 'error':
            self.error('; '.join(response.messages))

    def cancel(self) -> None:
        """Trigger the cancel status
        """
        log.debug(f'Cancelling job {self.uid}')
        if self.get_status() != QueueItemStatus.IS_WAITING:
            raise ValueError(f'Cannot cancel a job that is not in the WAITING state ({self.uid}).')
        self.cancelled_timestamp = dt.datetime.now().astimezone()

    def complete(self, client: TomtomClient) -> None:
        """Trigger the completed status


        Parameters
        ----------
        client : TomtomClient
            The client is needed to gain additional information on how the job went.

        Raises
        ------
        ValueError
            if this item status is not submitted
        """
        log.debug(f'Completing job {self.uid}')
        if self.get_status() != QueueItemStatus.SUBMITTED:
            raise ValueError(
                f'To be completed, the status of job {self.uid} should be SUBMITTED, not {self.get_status()}.')
        self.completed_timestamp = dt.datetime.now().astimezone()

        info = client.status(job_id=self.tomtom_job_id)
        if info.job_state != TomtomJobState.DONE:
            self.error(f'The job {self.uid} has been marked by tomtom as {info.job_state.name}')

        self.erase()

    def get_status(self) -> QueueItemStatus:
        """Get the status of this queued item

        Returns
        -------
        QueueItemStatus
            This queued item status.
        """
        if not pd.isna(self.error_timestamp):
            return QueueItemStatus.HAS_ERROR
        elif not pd.isna(self.completed_timestamp):
            return QueueItemStatus.COMPLETED
        elif not pd.isna(self.submitted_timestamp):
            return QueueItemStatus.SUBMITTED
        elif not pd.isna(self.cancelled_timestamp):
            return QueueItemStatus.CANCELED
        else:
            return QueueItemStatus.IS_WAITING
