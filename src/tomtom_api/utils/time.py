"""Utility functions grouped by theme: time"""
import calendar
import datetime as dt
from typing import List, Union


def date_as_str(date: Union[str, dt.datetime, dt.date], date_format: str) -> str:
    """
    Get the given date as a string.
    In the meantime, assert that the returned date is at a given format.

    Parameters
    ----------
    date: Union[str, dt.datetime, dt.date]
        The date to "convert" to string. If the date is a string, this might raise an exception.
    date_format: str
        The date format that the output string must have

    Returns
    -------
    str
        The given date at the given format

    Raises
    ------
    ValueError
        if the given date is a string that does not match the given format.
    ValueError
        if the input date does not match the input types
    """
    # ugly hack to bypass python strict rule of preventing the use of the '24:00' notation.
    if isinstance(date, str) and date == '24:00':
        return date

    if isinstance(date, str):
        _ = dt.datetime.strptime(date, date_format)
        return date
    elif isinstance(date, dt.date):
        return dt.datetime(date.year, date.month, date.day).strftime(date_format)
    elif isinstance(date, dt.datetime):
        return date.strftime(date_format)
    else:
        raise ValueError(f'Cannot generate a date string from {type(date)}')


def dow(days: List[str]) -> List[str]:
    """
    Assert that the given list is a well formatted list of days, containing only the 3 first letter of the day,
    capitalized.

    Parameters
    ----------
    days: List[str]
        The list of days to check

    Returns
    -------
    List[str]
        The list of days, we are now certain that they have 3 capitalized letters corresponding to a day of week

    Raises
    ------
    ValueError
        if at least one element in the list is not correct.
    """
    all_dow = {d.upper() for d in calendar.day_abbr}
    days = [d.upper() for d in days]
    if not all([d in all_dow for d in days]):
        raise ValueError('At least one of the input in `days` is not a 3 first letters day word.')
    return days


def time_range(start: Union[dt.datetime, str] = '00:00', end: Union[dt.datetime, str] = '24:00', interval: str = '15T') -> List[str]:
    """
    Generate an array of strings containing all time ranges of the selected interval between the two hours given.

    Parameters
    ----------
    start: Union[dt.datetime, str]
        The start *time* for this time range.
        dt.datetime object will ignore everything but the hour & minute attributes.
        str must be in the following format: '%H:%M'.
    end: Union[dt.datetime, str]
        The end *time* for this time range.
        dt.datetime object will ignore everything but the hour & minute attributes.
        str must be in the following format: '%H:%M'.
    interval: str
        The interval of a time range.

    Returns
    -------
    List[str]
        The list of time ranges

    Examples
    --------
    >>> all_time_range()
    ['00:00-00:15', '00:15-00:30', ..., '23:30-23:45', '23:45-24:00']
    >>> time_range('15:12', '17:00', '4T')
    ['15:12-15:16', '15:16-15:20', '15:20-15:24', '15:24-15:28', '15:28-15:32', '15:32-15:36', '15:36-15:40', '15:40-15:44', '15:44-15:48', '15:48-15:52', '15:52-15:56', '15:56-16:00', '16:00-16:04', '16:04-16:08', '16:08-16:12', '16:12-16:16', '16:16-16:20', '16:20-16:24', '16:24-16:28', '16:28-16:32', '16:32-16:36', '16:36-16:40', '16:40-16:44', '16:44-16:48', '16:48-16:52', '16:52-16:56', '16:56-17:00']
    """
    import pandas as pd
    time_format = '%H:%M'

    start, end = date_as_str(start, time_format), date_as_str(end, time_format)
    end = end if end != '24:00' else "00:00"

    (start_hour, start_minute), (end_hour, end_minute) = start.split(':'), end.split(':')
    start_hour, start_minute, end_hour, end_minute = int(start_hour), int(start_minute), int(end_hour), int(end_minute)

    start, end = dt.datetime(2000, 1, 1, start_hour, start_minute), dt.datetime(2000, 1, 1, end_hour, end_minute)
    if end.hour == 0 and end.minute == 0:
        end += dt.timedelta(days=1)

    times = pd.date_range(start=start, end=end, freq=interval)
    times = [t.strftime(time_format) for t in times]
    if times[-1] == '00:00':
        times[-1] = '24:00'
    time_ranges = [f"{start}-{end}" for start, end in zip(times[:-1], times[1:])]

    return time_ranges
