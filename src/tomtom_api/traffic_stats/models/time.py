"""Time models

Collections of different models that are used in the `tomtom_api` module.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Union

from tomtom_api.traffic_stats import MAX_DATE_RANGE_LENGTH
from tomtom_api.utils.time import date_as_str, dow, time_range


class TomtomDateRange:
    """Data structure allowing to store a date range, with a name and some exclusions"""
    name: str
    # 'from', %Y-%m-%d
    start: str
    # 'to', %Y-%m-%d
    end: str

    # %Y-%m-%d
    exclusions: Optional[List[str]] = None
    # 3 first letters of string day, capitalized
    excluded_days_of_week: Optional[List[str]] = None

    def __init__(
        self,
        name: str,
        start: Union[str, dt.datetime, dt.date],
        end: Union[str, dt.datetime, dt.date],
        exclusions: Optional[List[Union[str, dt.datetime, dt.date]]] = None,
        excluded_days_of_week: Optional[List[str]] = None
    ):
        """
        Documentation: https://developer.tomtom.com/traffic-stats/documentation/api/route-analysis#structure-of-dateranges1

        Parameters
        ----------
        name : str
            Date range name. Given for the users's convenience.
        start : Union[str, dt.datetime, dt.date]
            Date from (inclusive)
        end : Union[str, dt.datetime, dt.date]
            Date to (inclusive)
        exclusions : Optional[List[Union[str, dt.datetime, dt.date]]], optional
            List of days excluded from the date range, by default None
        excluded_days_of_week : Optional[List[str]], optional
            List of days of the week to be excluded, by default None

        Raises
        ------
        ValueError
            If a conversion is impossible or if an API limitation rule has been reached.
        """
        self.name = name

        date_fmt = '%Y-%m-%d'
        self.start = date_as_str(start, date_fmt)
        self.end = date_as_str(end, date_fmt)

        s = dt.datetime.strptime(self.start, date_fmt)
        e = dt.datetime.strptime(self.end, date_fmt)
        if e < s:
            raise ValueError(f'The start date ({self.start}) is after the end date ({self.end})')
        if (e - s).days > MAX_DATE_RANGE_LENGTH:
            raise ValueError('The given date range is greater than the maximum allowed.')

        self.exclusions = None if exclusions is None else [date_as_str(d, date_fmt) for d in exclusions]
        self.excluded_days_of_week = None if excluded_days_of_week is None else dow(excluded_days_of_week)

    @classmethod
    def from_week(cls, year: int, week: int, **kwargs) -> TomtomDateRange:
        """Helper to create date range of one week.
        The name can still be overridden by the kwargs, otherwise a string containing the year and week will be 
        generated.
        This generates a week starting a Monday and ending a Sunday.


        Parameters
        ----------
        year : int
            The year of the date range.
        week : int
            The week of the date range.

        Returns
        -------
        TomtomDateRange
            A week range.

        Raises
        ------
        ValueError
            If 'start' or 'end' have been passed as kwargs, or if the genuine constructor raises a ValueError.
        """
        forbidden_kwargs = [k for k in ['start', 'end'] if k in kwargs]
        if len(forbidden_kwargs) > 0:
            raise ValueError(
                f"You cannot specify {' nor '.join(forbidden_kwargs)} when calling `TomtomDateRange.from_week`."
            )

        monday = dt.datetime.strptime(f'{year}-{week}-1', '%Y-%W-%w')
        sunday = dt.datetime.strptime(f'{year}-{week}-0', '%Y-%W-%w')
        name = kwargs.pop('name', f'Week {week} of year {year}')
        return cls(name, monday, sunday, **kwargs)

    @classmethod
    def from_dict(cls, dict_object: Dict[str, Any]) -> TomtomDateRange:
        return cls(
            name=dict_object['name'],
            start=dict_object['from'],
            end=dict_object['to'],
            exclusions=None if 'exclusions' not in dict_object else dict_object['exclusions'],
            excluded_days_of_week=None if 'excludedDaysOfWeek' not in dict_object else dict_object['excludedDaysOfWeek']
        )

    def to_dict(self) -> Dict[str, Any]:
        """Transform this data type to a python dictionary.
        This dict is meant to be used to generate the payload given to some Tomtom API endpoints.

        Returns
        -------
        Dict[str, float]
            The dictionary with the keys specified in the documentation.
        """
        date_dict = {
            'name': self.name,
            'from': self.start,
            'to': self.end,
        }

        if self.exclusions is not None:
            date_dict['exclusions'] = self.exclusions
        if self.excluded_days_of_week is not None:
            date_dict['excludedDaysOfWeek'] = self.excluded_days_of_week

        return date_dict


class TomtomTimeGroup:
    """Element of the `TomtomTimeSet`"""
    days: List[str]
    # %H:%M-%H:%M
    times: List[str]

    def __init__(self, days: List[str], times: List[str]):
        """Time group in a time set.

        Parameters
        ----------
        days : List[str]
            Days of the week for the time group list values. 3 first letters of string day, capitalized
        times : List[str]
            Time ranges for the time group with the list of values in the format HH:mm-HH:mm
        """
        self.days = dow(days)

        hour_fmt = '%H:%M'
        tuple_times = [t.split('-') for t in times]
        self.times = [f'{date_as_str(t[0], hour_fmt)}-{date_as_str(t[1], hour_fmt)}' for t in tuple_times]

    @classmethod
    def from_dict(cls, dict_object: Dict[str, Any]) -> TomtomTimeGroup:
        return cls(
            days=dict_object['days'],
            times=dict_object['times']
        )

    def to_dict(self) -> Dict[str, List[str]]:
        """Transform this data type to a python dictionary.
        This dict is meant to be used to generate the payload given to some Tomtom API endpoints.

        Returns
        -------
        Dict[str, float]
            The dictionary with the keys specified in the documentation.
        """
        return self.__dict__

    @classmethod
    def from_time_range(
        cls,
        start: Union[str, dt.datetime] = '00:00',
        end: Union[str, dt.datetime] = '24:00',
        interval: str = '15T'
    ) -> TomtomTimeGroup:
        """
        Alternative constructor for the TomtomTimeGroup class that will generate time range.
        See `tomtom_api.utils.time.time_range` for more information about the parameters.

        Parameters
        ----------
        start : Union[str, dt.datetime]
            The start time, by default '00:00'
        end : Union[str, dt.datetime]
            The end time, by default '24:00'
        interval : str
            The interval of a time range, by default '15T'

        Returns
        -------
        TomtomTimeGroup
        """
        dow = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        times = time_range(start, end, interval)
        return cls(days=dow, times=times)

    def split_by_time(self) -> List[TomtomTimeGroup]:
        """
        Generate one TomtomTimeGroup by time element in this object.

        Returns
        -------
        List[TomtomTimeGroup]
        """
        return [TomtomTimeGroup(days=self.days, times=[time]) for time in self.times]


class TomtomTimeSet:
    """Group of tomtom time groups"""
    name: str
    time_groups: List[TomtomTimeGroup]

    def __init__(self, name: str, time_groups: List[TomtomTimeGroup]):
        """Data structure containing a list of time groups
        Documentation: https://developer.tomtom.com/traffic-stats/documentation/api/route-analysis#structure-of-timesets1

        Parameters
        ----------
        name : str
            Time set name. Given for user's convenience.
        time_groups : List[TomtomTimeGroup]
            Time groups in a time set.
        """
        self.name = name
        self.time_groups = time_groups

    @classmethod
    def from_dict(cls, dict_object: Dict[str, Any]) -> TomtomTimeSet:
        return cls(
            name=dict_object['name'],
            time_groups=[TomtomTimeGroup.from_dict(t) for t in dict_object['timeGroups']]
        )

    def to_dict(self):
        """Transform this data type to a python dictionary.
        This dict is meant to be used to generate the payload given to some Tomtom API endpoints.

        Returns
        -------
        Dict[str, float]
            The dictionary with the keys specified in the documentation.
        """
        return {
            'name': self.name,
            'timeGroups': [tg.to_dict() for tg in self.time_groups]
        }

    def split_by_time(self) -> List[TomtomTimeSet]:
        """
        Generate one TomtomTimeSet by time in each time_group of this object.

        Returns
        -------
        List[TomtomTimeSet]
        """
        tab = []
        for time_group in self.time_groups:
            for splitted_time_group in time_group.split_by_time():
                tab.append(TomtomTimeSet(f'{self.name} ({splitted_time_group.times[0]})', [splitted_time_group]))

        return tab
