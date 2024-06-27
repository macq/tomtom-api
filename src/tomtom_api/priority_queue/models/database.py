from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from tomtom_api import config
from tomtom_api.priority_queue.models.queue import QueueItem
from tomtom_api.priority_queue.models.status import QueueItemStatus
from tomtom_api.utils.singleton import SingletonMeta

DATABASE_FILE = config.path.home / 'db.parquet'


class PriorityQueueDB(metaclass=SingletonMeta):
    # The file that contains the data
    file: Path
    # The dataframe loaded from the file containing the data
    df: pd.DataFrame
    # The list of the columns that compose the dataframe
    columns: List[str] = [
        'uid',
        'name',
        'report_type',
        'payload_link',
        'priority',
        'created_timestamp',
        'updated_timestamp',
        'submitted_timestamp',
        'completed_timestamp',
        'cancelled_timestamp',
        'error_timestamp',
        'tomtom_job_id',
    ]

    def __init__(self):
        super().__init__()
        self.file = DATABASE_FILE
        self.df = None
        self.read()

    def _force_col_types(self) -> None:
        for time_col in ['created_timestamp',
                         'updated_timestamp',
                         'submitted_timestamp',
                         'completed_timestamp',
                         'cancelled_timestamp',
                         'error_timestamp']:
            self.df[time_col] = pd.to_datetime(self.df[time_col])

    def read(self) -> None:
        """Read the file and store the content in the dataframe attribute.
        """
        if not self.file.exists():
            self.df = pd.DataFrame(columns=self.columns)
        else:
            self.df = pd.read_parquet(self.file)
        self._force_col_types()

    def write(self) -> None:
        """Write the content of the dataframe into the file.
        """
        # try to prevent as much data race as possible by re-reading the dataset before writing it.
        current_df = self.df.copy()
        self.read()
        self.df = pd.concat([current_df, self.df]).drop_duplicates(subset=['uid'], keep='first')

        self.file.unlink(missing_ok=True)
        self.df['payload_link'] = self.df['payload_link'].map(str)
        self.df.to_parquet(self.file)

    def add(self, item: QueueItem) -> None:
        """Add the given element as a new row in the dataframe.

        The element object is responsible for maintaining its data and keep the same 'payload_link' for all its
        lifetime.

        Parameters
        ----------
        item : QueueItem
            The item that should be added to this PriorityQueueDatabase.
        """
        data = {k: item.__dict__[k] for k in self.columns}
        data['report_type'] = item.payload.__class__.__name__
        self.df = pd.concat([self.df, pd.DataFrame([data])])
        self._force_col_types()

    def get_next(self, n: int = 1) -> List[QueueItem]:
        """Get the list of the next element(s)

        The next element method is deterministic and follows those rules:
            - The next element should hold any of the following statuses: submitted, completed, canceled or error
            - The higher the priority is, the sooner it will be taken
            - The older the element is, the sooner it will be taken

        Parameters
        ----------
        n : int, optional
            The maximum number of next element that should be returned, by default 1

        Returns
        -------
        List[QueueItem]
            The ordered list of the next elements that should be submitted to the Tomtom API.
        """
        not_submitted = self.df['submitted_timestamp'].isnull()
        not_completed = self.df['completed_timestamp'].isnull()
        not_cancelled = self.df['cancelled_timestamp'].isnull()
        not_error = self.df['error_timestamp'].isnull()
        next_items = self.df[not_submitted & not_completed & not_cancelled & not_error] \
            .sort_values(['priority', 'created_timestamp'], ascending=[False, True]) \
            .to_dict(orient='records')
        return [QueueItem.from_dict(**item) for item in next_items[:n]]

    def get_filtered_items(
        self,
        uid: Optional[List[str]] = None,
        name: Optional[List[str]] = None,
        priority: Optional[List[str]] = None,
        status: Optional[List[QueueItemStatus]] = None,
    ) -> List[QueueItem]:
        """Provide a filtered list of the queued items.

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
            The filtered list of queued items.
        """
        length = len(self.df)
        if length < 1:
            return []
        uid, name, priority, status = uid or [], name or [], priority or [], status or []

        # uid filter
        uid_filter_str = '' if len(uid) < 1 else '(uid in @uid)'

        # name filter
        name_filters = [f'name.str.contains("{n}")' for n in name]
        name_filter_str = ' or '.join(name_filters)
        name_filter_str = f'({name_filter_str})' if name_filter_str != '' else ''

        # priority filter
        priority_filters = []
        for p in priority:
            if p.startswith('<') or p.startswith('>'):
                priority_filters.append(f'priority {p}')
            else:
                priority_filters.append(f'priority = {p}')

        priority_filter_str = f"{' and '.join(priority_filters)}"

        # concat the query
        query = ' and '.join([f for f in [uid_filter_str, name_filter_str, priority_filter_str] if f != ''])

        # perform the query
        if query == '':
            filtered_df = self.df
        else:
            filtered_df = self.df.query(query)

        # status filter
        items = [QueueItem.from_dict(**row) for row in filtered_df.to_dict(orient="records")]
        tab = [i for i in items if len(status) < 1 or i.get_status() in status]

        return tab

    def update(self, items: List[QueueItem], force_write: bool = False) -> None:
        """Update elements
        Under the hood this method will delete the database items that have the uid present in the provided list of
        elements, then add the provided list of elements.

        This was not intended but due to this internal implementation, it is possible to use this function for bulk
        insert of new elements.

        Parameters
        ----------
        items : List[QueueItem]
            The list of to-be-updated elements
        force_write : bool, optional
            True to force the writing on the file, by default False
        """
        uids = [i.uid for i in items]
        self.df = self.df[~self.df['uid'].isin(uids)]
        for item in items:
            self.add(item)

        if force_write:
            self.write()

    def describe(self) -> Dict[str, float]:
        """Provide insight and metrics related to the database usage and tomtom job completion.

        Returns
        -------
        Dict[str, float]
            Various metrics
        """
        completed_mask = ~self.df['completed_timestamp'].isnull()
        no_error_mask = self.df['error_timestamp'].isnull()

        completed_df = self.df[completed_mask & no_error_mask]
        completed_df['completion'] = completed_df['completed_timestamp'] - completed_df['submitted_timestamp']
        completed_df['completion_minute'] = completed_df['completion'].map(lambda delta: delta.total_seconds()/60)

        return {
            'n_items_total': len(self.df),
            'n_items_waiting': len(self.get_filtered_items(status=[QueueItemStatus.IS_WAITING])),
            'n_items_submitted': len(self.get_filtered_items(status=[QueueItemStatus.SUBMITTED])),
            'n_items_canceled': len(self.get_filtered_items(status=[QueueItemStatus.CANCELED])),
            'n_items_completed': len(self.get_filtered_items(status=[QueueItemStatus.COMPLETED])),
            'n_items_error': len(self.get_filtered_items(status=[QueueItemStatus.HAS_ERROR])),
            'completion_time_avg_minute': completed_df['completion_minute'].mean(),
            'completion_time_min_minute': completed_df['completion_minute'].min(),
            'completion_time_max_minute': completed_df['completion_minute'].max(),
            'completion_time_std_minute': completed_df['completion_minute'].std()
        }

    def empty(self) -> None:
        """Empty the database
        """
        self.df = pd.DataFrame(columns=self.columns)
        self._force_col_types()
