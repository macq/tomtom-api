from typing import List, Literal

import pytest
from shapely import wkt

from tomtom_api.client import DummyTomtomClient, TomtomClient
from tomtom_api.priority_queue.lib import (priority_queue_clean_folder,
                                           priority_queue_list_next)
from tomtom_api.traffic_stats.models.geospatial import (TomtomNetwork,
                                                        TomtomPoint,
                                                        TomtomRoad)
from tomtom_api.traffic_stats.models.jobs.area import TomtomAreaJob
from tomtom_api.traffic_stats.models.jobs.base import TomtomJob
from tomtom_api.traffic_stats.models.jobs.route import TomtomRouteJob
from tomtom_api.traffic_stats.models.time import (TomtomDateRange,
                                                  TomtomTimeGroup,
                                                  TomtomTimeSet)


@pytest.fixture
def init_test() -> None:
    priority_queue_clean_folder()
    assert len(priority_queue_list_next()) == 0
    yield


@pytest.fixture
def client() -> TomtomClient:
    yield DummyTomtomClient(key='macqisgreat')


def get_jobs(n: int, job_type: Literal['TomtomRoadJob', 'TomtomAreaJob']) -> List[TomtomJob]:
    road = TomtomRoad(
        'Some Route',
        start=TomtomPoint(51.7822, 4.61689),
        end=TomtomPoint(51.78555, 4.61076),
        via=[TomtomPoint(51.78153, 4.60559)],
        full_traversal=False,
        zone_id='Europe/Amsterdam',
        probe_source='ALL'
    )

    poly_wkt = "POLYGON ((3.372868711495414 50.6166759414709, 3.372868711495414 50.594641815304584, 3.4175386177699068 50.594641815304584, 3.4175386177699068 50.6166759414709, 3.372868711495414 50.6166759414709))"
    network = TomtomNetwork('Square close to Tournai',
                            geometry=wkt.loads(poly_wkt),
                            time_zone_id='Europe/Brussels'
                            )

    date_range = TomtomDateRange(
        'Last working week of January',
        start='2021-01-25',
        end='2021-01-29',
        exclusions=["2021-01-26", "2021-01-27"]
    )
    time_set = TomtomTimeSet(
        name='Monday morning hour',
        time_groups=[TomtomTimeGroup(days=['MON'], times=['7:00-8:00'])])

    tab = []
    for i in range(n):
        if job_type == 'TomtomRoadJob':
            tab.append(TomtomRouteJob(job_name=f'{road.name}_{i}',
                                      routes=[road],
                                      date_ranges=[date_range],
                                      time_sets=[time_set],
                                      distance_unit='KILOMETERS',
                                      accept_mode='AUTO',
                                      map_version=2023.03))
        elif job_type == 'TomtomAreaJob':
            tab.append(TomtomAreaJob(job_name=f'{network.name}_{i}',
                                     network=network,
                                     date_range=date_range,
                                     time_sets=[time_set],
                                     distance_unit='KILOMETERS',
                                     accept_mode='AUTO',
                                     map_version=2023.03))
    return tab


@pytest.fixture
def road_job():
    yield get_jobs(1, 'TomtomRoadJob')[0]


@pytest.fixture
def area_job():
    yield get_jobs(1, 'TomtomAreaJob')[0]


@pytest.fixture
def some_road_jobs():
    yield get_jobs(3, 'TomtomRoadJob')


@pytest.fixture
def some_area_jobs():
    yield get_jobs(3, 'TomtomAreaJob')
