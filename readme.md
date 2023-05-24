# Tomtom API

API client allowing to interact with the tomtom REST services.

This module is focused around the *Traffic Stats* service.

More information about this service can be found [here](https://developer.tomtom.com/traffic-stats/documentation/product-information/introduction).
The API documentation can be found [here](https://developer.tomtom.com/traffic-stats/documentation/api/introduction).

## Installation

```bash
# Create a virtual environment
python -m virtualenv venv_tomtom_api
source venv_tomtom_api/bin/activate

# Install static requirements (Optional)
pip install -r requirements.txt

# Install the package itself
pip install .
```

## Usage

### Configuration

This project is using environment variable as configuration.

You are encouraged to store all your environment variable in a `.env` file at the root of your folder so it looks like this:

```bash
TOMTOM_API_KEY=mysuperkey
TOMTOM_API_VERSION=1
TOMTOM_API_LOG_LEVEL=debug
TOMTOM_API_PROXY_IP=172.0.10.1
TOMTOM_API_PROXY_PORT=1234
TOMTOM_API_PROXY_USERNAME=user
TOMTOM_API_PROXY_PASSWORD=password
TOMTOM_API_HOME_FOLDER=/var/lib/tomtom_api
TOMTOM_API_QUEUE_LOOP_DURATION=60
```

To check the available names of the environment variables, you can use the command `python -m tomtom_api list-env`.

To load all your environment variables, you can use the command `export $(cat .env)`.

### CLI

There are a few actions available through a CLI.
You can list all the commands with `python -m tomtom_api --help`.

```
❯ python -m tomtom_api --help
Usage: python -m tomtom_api [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  get-job-info       Display information about a specific job.
  list-all-job-info  Fetch information about the jobs registered.
  list-env           List the configurable environment variables.
  proxy-check        Get your ip with and without the configured proxy.
```

### Module

Some endpoints are not available through the CLI because it is not easy to provide the required structure of the payload.
Then you can import this module in your python script and launch requests through the `TomtomClient`.

Here's how to mimic the payload present in the documentation example:
```python
from tomtom_api.client import TomtomClient
from tomtom_api.traffic_stats.models.geospatial import TomtomPoint, TomtomRoad
from tomtom_api.traffic_stats.models.time import (TomtomDateRange,
                                                  TomtomTimeGroup,
                                                  TomtomTimeSet)

client = TomtomClient()

road = TomtomRoad(
    'Some Route',
    start=TomtomPoint(51.7822, 4.61689),
    end=TomtomPoint(51.78555, 4.61076),
    via=[TomtomPoint(51.78153, 4.60559)],
    full_traversal=False,
    zone_id='Europe/Amsterdam',
    probe_source='ALL'
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

response = client.route_analysis(
    'Test job',
    distance_unit='KILOMETERS',
    map_version=2020.09,
    accept_mode='AUTO',
    roads=[road],
    date_ranges=[date_range],
    time_sets=[time_set]
)
```

And here's another example, just for fun:
```python
import calendar
import datetime as dt

import pandas as pd

from tomtom_api.client import TomtomClient
from tomtom_api.traffic_stats.models.geospatial import TomtomPoint, TomtomRoad
from tomtom_api.traffic_stats.models.time import (TomtomDateRange,
                                                  TomtomTimeGroup,
                                                  TomtomTimeSet)

# Geospatial information
start = TomtomPoint(50.881238, 4.434957)
via = [
    TomtomPoint(50.880040, 4.435190),
    TomtomPoint(50.878715, 4.431446),
    TomtomPoint(50.877617, 4.420429),
    TomtomPoint(50.877287, 4.415166),
    TomtomPoint(50.877193, 4.413980),
]
end = TomtomPoint(50.877779, 4.413870)

roads = [
    TomtomRoad('Rue de la fusée, Evere, Belgique',
               probe_source='ALL',
               start=start,
               end=end,
               via=via,
               full_traversal=False,
               zone_id='Europe/Brussels')
]

# Time information
time_group_all_week = TomtomTimeGroup.from_time_range()
time_sets_all_week = [TomtomTimeSet('All week, every 15min', [time_group_all_week])]
date_ranges = [TomtomDateRange.from_week(2022, 30)]

# Client
client = TomtomClient()
response = client.route_analysis('Testing from home',
                                 distance_unit='KILOMETERS',
                                 roads=roads,
                                 date_ranges=date_ranges,
                                 time_sets=time_sets_all_week)
```