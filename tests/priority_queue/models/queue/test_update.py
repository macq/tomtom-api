
import pytest

from tomtom_api.priority_queue.lib import (priority_queue_add_job,
                                           priority_queue_list_all,
                                           priority_queue_list_next,
                                           priority_queue_update_job)
from tomtom_api.priority_queue.models.database import PriorityQueueDB
from tomtom_api.priority_queue.models.status import QueueItemStatus


def test_update(init_test, client, area_job):
    priority_queue_add_job(area_job.job_name, area_job, 5)
    db = PriorityQueueDB()
    job = priority_queue_list_next()[0]

    new_name = 'hey it is new name'
    priority_queue_update_job(job.uid, name=new_name, cancel=True)
    j = priority_queue_list_all(uid=job.uid)[0]
    assert j.name == new_name
    assert j.get_status() == QueueItemStatus.CANCELED

    priority_queue_update_job(job.uid, cancel=False)
    j = priority_queue_list_all(uid=job.uid)[0]
    assert j.name == new_name
    assert j.get_status() == QueueItemStatus.IS_WAITING

    j.submit(client)
    db.update([j])

    j.get_status() == QueueItemStatus.SUBMITTED

    with pytest.raises(ValueError):
        priority_queue_update_job(uid=job.uid, name='should fail')

    j.complete(client)
    db.update([j])

    with pytest.raises(ValueError):
        priority_queue_update_job(uid=job.uid, name='should also fail')
