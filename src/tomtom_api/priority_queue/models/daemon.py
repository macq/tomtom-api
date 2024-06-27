import logging
from pathlib import Path
from time import sleep
from typing import List, Optional

from tomtom_api import config, log
from tomtom_api.client import TomtomClient
from tomtom_api.priority_queue.models.database import PriorityQueueDB
from tomtom_api.priority_queue.models.queue import QueueItem
from tomtom_api.priority_queue.models.status import QueueItemStatus
from tomtom_api.traffic_stats import N_CONCURRENT_JOB_IN_PROGRESS
from tomtom_api.traffic_stats.models.status import (TomtomJobState)
from tomtom_api.utils.daemon import Daemon

DAEMON_LOG_FILE = config.path.home / 'daemon.log'


class PriorityQueueDaemon(Daemon):
    def __init__(self,
                 pid_file: Optional[Path] = None,
                 stdin: Path = Path('/dev/null'),
                 stdout: Path = Path('/dev/null'),
                 stderr: Path = Path('/dev/null')
                 ):
        pid_file = config.path.home / 'daemon-tomtom-api.pid' if pid_file is None else Path(pid_file)
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(pid_file, stdin, stdout, stderr)

    def run(self):
        # add a file log handler since we won't see anything in STDOUT
        # because all standard input are redirected to /dev/null
        file_handler = logging.FileHandler(DAEMON_LOG_FILE, encoding='utf-8')
        file_handler.setFormatter(log.handlers[0].formatter)
        file_handler.setLevel(config.log.level.upper())
        log.addHandler(file_handler)

        # init client
        client = TomtomClient()

        # init db
        db = PriorityQueueDB()

        # states for "In progress"
        in_progress_states = [TomtomJobState.NEW,
                              TomtomJobState.MAPMATCHED,
                              TomtomJobState.MAPMATCHING,
                              TomtomJobState.READING_GEOBASE,
                              TomtomJobState.CALCULATIONS,
                              TomtomJobState.SCHEDULED]

        while True:
            log.debug('Daemonic loop starting.')
            sleep(config.queue.loop_duration)
            db.read()
            try:
                log.debug('Checking the number of tomtom jobs that are IN PROGRESS.')
                in_progress_jobs = client.search_jobs(state=in_progress_states)
                n = in_progress_jobs.total_elements

                if n < N_CONCURRENT_JOB_IN_PROGRESS:
                    log.info(f'There are {N_CONCURRENT_JOB_IN_PROGRESS - n} available spots on tomtom side.')

                    # 1: find old submitted job(s) and mark them as completed
                    tomtom_job_in_progress_ids = [c.job_id for c in in_progress_jobs.content]
                    submitted_items: List[QueueItem] = db.get_filtered_items(status=[QueueItemStatus.SUBMITTED])

                    # the items that should be marked as complete are the one that are tagged by ourselves as
                    # "submitted" but that are not (anymore) in the tomtom "in progress" jobs.
                    should_be_complete_items: List[QueueItem] = [
                        j for j in submitted_items
                        if j.tomtom_job_id not in tomtom_job_in_progress_ids
                    ]

                    # then mark all the jobs that should be complete as "complete".
                    for item in should_be_complete_items:
                        item.complete(client)
                        log.info(f'Completed item {item.uid} (tomtom job {item.tomtom_job_id})')
                    db.update(should_be_complete_items, True)

                    # 2: find next job(s) and submit them
                    for item in db.get_next(N_CONCURRENT_JOB_IN_PROGRESS - n):
                        item.submit(client)
                        log.info(f'Submitted item {item.uid} as tomtom job {item.tomtom_job_id}.')
                        db.update([item], True)

            # We don't want the daemon to exit because of some unmanaged exception
            except Exception as e:
                log.critical(str(e))
