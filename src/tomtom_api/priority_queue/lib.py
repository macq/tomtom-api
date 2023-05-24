import json
from pathlib import Path
from typing import List, Optional, Union

from tomtom_api import config, log
from tomtom_api.priority_queue.models.database import PriorityQueueDB
from tomtom_api.priority_queue.models.queue import QueueItem
from tomtom_api.priority_queue.models.status import QueueItemStatus
from tomtom_api.traffic_stats.models.jobs.route import TomtomRouteJob


def priority_queue_add_job(name: str, data: Union[TomtomRouteJob, Path], priority: int) -> None:
    """Add a job to the priority queue

    The higher the priority, the sooner the job will be submitted to the Tomtom API.

    Parameters
    ----------
    name : str
        The name of the job
    data : Union[TomtomJob, Path]
        The TomtomJob that needs to be submitted to the Tomtom API. A path to a file containing a JSON encoded
        TomtomJob is also valid.
    priority : int
        The priority of the job.
    """
    queue_item = QueueItem.new(name, data, priority)

    db = PriorityQueueDB()
    db.add(queue_item)
    db.write()
    log.debug(f'The job {queue_item.uid} has been added to the queue.')


def priority_queue_list_all(
    uid: Optional[Union[str, List[str]]] = None,
    name: Optional[Union[str, List[str]]] = None,
    priority: Optional[Union[str, List[str]]] = None,
    status: Optional[Union[QueueItemStatus, List[QueueItemStatus]]] = None,
) -> List[QueueItem]:
    """List the queued items from the database. Filters can be applied to prune this list.

    There is an AND operator between the different filters.

    Parameters
    ----------
    uid : Optional[Union[str, List[str]]], optional
        Provide uids to filter on them. There is an OR operator between the different uid provided. by default None
    name : Optional[Union[str, List[str]]], optional
        Provide names to filter on them. There is an OR operator between the different names provided. by default None
    priority : Optional[Union[str, List[str]]], optional
        Provide priority strings to filter the jobs based on the priority. It is also possible to provide
        inferior/superior (or equal) signs. There is a AND operator between the different priorities provided.
        by default None
    status : Optional[Union[QueueItemStatus, List[QueueItemStatus]]], optional
        Provide statuses to filter the jobs based on their status. There is an OR operator between the different
        statuses provided. by default None

    Returns
    -------
    List[QueueItem]
        The list of the items in the queue.
    """
    uid = uid if isinstance(uid, list) else [] if uid is None else [uid]
    name = name if isinstance(name, list) else [] if name is None else [name]
    priority = priority if isinstance(priority, list) else [] if priority is None else [priority]
    status = status if isinstance(status, list) else [] if status is None else [status]

    db = PriorityQueueDB()
    items = db.get_filtered_items(uid, name, priority, status)
    return items


def priority_queue_list_next(n: int = 1) -> List[QueueItem]:
    """List the next items that will be submitted to the Tomtom API

    Parameters
    ----------
    n : int, optional
        The number of next items to be submitted, by default 1

    Returns
    -------
    List[QueueItem]
        The list of the next items.
    """
    db = PriorityQueueDB()
    return db.get_next(n)


def priority_queue_clean_folder():
    """Delete all files that have been created for the priority queue.
    """
    from tomtom_api.priority_queue.models.daemon import DAEMON_LOG_FILE
    from tomtom_api.priority_queue.models.database import DATABASE_FILE

    home_folder = config.path.home
    payload_folder = home_folder / 'payloads'

    db = PriorityQueueDB()
    db.empty()

    for f in [DATABASE_FILE, DAEMON_LOG_FILE]:
        f.unlink(missing_ok=True)

    if payload_folder.exists():
        for file in payload_folder.iterdir():
            file.unlink(missing_ok=True)
        payload_folder.rmdir()


def priority_queue_update_job(
    uid: str,
    name: Optional[str] = None,
    priority: Optional[int] = None,
    cancel: Optional[bool] = None,
    data: Optional[Union[TomtomRouteJob, Path]] = None,
) -> None:
    """Update a job already present in the priority queue.

    Those jobs are identified by their uid, so you will never be able to update this field.
    At least one of the other argument must be provided, otherwise it is useless to call this function.

    Fields that do not change do not need to be provided.

    Parameters
    ----------
    uid : str
        The identifier of the queued item.
    name : Optional[str], optional
        The new name of the queued item, by default None
    priority : Optional[int], optional
        The new priority of the queued item, by default None
    cancel : Optional[bool], optional
        True if the queued item should have the status "CANCELED". False if the queued item should loose this
        "CANCELED" status, by default None
    data : Optional[Union[TomtomJob, Path]], optional
        The new TomtomJob object for this queued item. A path to a file containing a JSON encoded
        TomtomJob is also valid. by default None
    """
    db = PriorityQueueDB()
    if data is not None:
        if isinstance(data, TomtomRouteJob):
            payload = data
        else:
            with open(data, 'r') as f:
                payload = TomtomRouteJob.from_dict(json.load(f))
    else:
        payload = None

    item: QueueItem = db.get_filtered_items(uid=uid)[0]
    item.update(name, priority, cancel, payload)
    db.update([item], force_write=True)


def pretty_print_queue(queue: List[QueueItem]) -> str:
    """Use the tabulate package to provide a pretty display of the items in the priority queue.

    Parameters
    ----------
    queue : List[QueueItem]
        The items that should be displayed.

    Returns
    -------
    str
        The pretty print of the provided items.
    """
    if len(queue) < 1:
        return ''

    from tabulate import tabulate
    tab = [{
        'UID': item.uid,
        'Tomtom ID': item.tomtom_job_id,
        'Status': item.get_status().name,
        'Priority': item.priority,
        'Creation': item.created_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        'Name': item.name
    } for item in queue]
    headers = {k: k for k in tab[0].keys()}
    return tabulate(tab, headers=headers, tablefmt='rounded_outline')
