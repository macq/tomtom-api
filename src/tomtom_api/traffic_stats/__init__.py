"""Limitations of the API

The API strictly states that there is some limitation applied to it and a job will be rejected if the request does not
respects the following constraints.
"""
MAX_ROAD_LENGTH = 200000  # in meters
MAX_ROAD_COUNT = 20
MAX_VIA_POINTS_COUNT = 150
MAX_DATE_RANGE_LENGTH = 366  # in days
MAX_DATE_RANGE_COUNT = 24
MAX_TIME_SETS_COUNT = 24
# number of jobs that will be computed concurrently on tomtom side.
# > At the same time you can have only 5 jobs in CALCULATIONS and SCHEDULED statuses per each developer key.
# > When you reach this limit you can still create new jobs as they will be queued until at least one of currently
# > running jobs is done.
# Source: https://developer.tomtom.com/traffic-stats/documentation/api/route-analysis#using-this-service
N_CONCURRENT_JOB_IN_PROGRESS = 5
MAX_NETWORK_AREA = 20000  # in km²
MAX_NAME_LENGTH = 100  # characters
