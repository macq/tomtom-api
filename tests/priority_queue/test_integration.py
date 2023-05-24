

from tomtom_api.priority_queue.lib import (priority_queue_add_job,
                                           priority_queue_list_all,
                                           priority_queue_list_next,
                                           priority_queue_update_job)
from tomtom_api.priority_queue.models.status import QueueItemStatus


def test_one_route_job(init_test, client, road_job):    # get the job
    # add the job to the list
    priority_queue_add_job(road_job.job_name, road_job, 5)

    # submit the next job
    next_job = priority_queue_list_next()[0]

    assert next_job.name == road_job.job_name
    assert next_job.get_status() == QueueItemStatus.IS_WAITING

    next_job.submit(client)

    assert next_job.get_status() == QueueItemStatus.SUBMITTED

    next_job.complete(client)

    assert next_job.get_status() == QueueItemStatus.COMPLETED


def test_one_area_job(init_test, client, area_job):
    # add it to the list
    priority_queue_add_job(area_job.job_name, area_job, 5)

    # submit the next job
    next_job = priority_queue_list_next()[0]

    assert next_job.name == area_job.job_name
    assert next_job.get_status() == QueueItemStatus.IS_WAITING

    next_job.submit(client)

    assert next_job.get_status() == QueueItemStatus.SUBMITTED

    next_job.complete(client)

    assert next_job.get_status() == QueueItemStatus.COMPLETED


def test_cancel_job(init_test, some_area_jobs):
    for j in some_area_jobs:
        priority_queue_add_job(j.job_name, j, 3)

    assert len(priority_queue_list_all()) == 3
    assert len(priority_queue_list_next(5)) == 3

    j = priority_queue_list_all()[1]
    priority_queue_update_job(j.uid, cancel=True)

    j = priority_queue_list_all(uid=j.uid)[0]
    assert j.get_status() == QueueItemStatus.CANCELED
    assert len(priority_queue_list_all()) == 3
    assert len(priority_queue_list_next(5)) == 2
