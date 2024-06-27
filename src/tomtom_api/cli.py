"""Definition of the available CLI"""
import datetime as dt
from sys import exit
from typing import List, Optional

import click

from tomtom_api import config
from tomtom_api.client import TomtomClient
from tomtom_api.traffic_stats.models.status import (TomtomJobState,
                                                    TomtomReportType)

date_fmt = '%Y-%m-%d'


#
# CLIENT CLI
#
# <editor-fold desc="CLIENT">

@click.group
def client():
    pass


@client.command
@click.option('--base-url', type=str,
              help=f'Base URL for calling the API. (Default is env {config.env.base_url}')
@click.option('--version', type=int, help=f'The API version (Default is env {config.env.version})')
@click.option('--key', type=str, help=f'Your API key. (Default is env {config.env.key})')
@click.option('-p', '--page-index', type=int, help='Index of a page with jobs.')
@click.option('-N', '--per-page', type=int, help='Number of jobs included in the page.')
@click.option('-a', '--created-after', type=click.DateTime(formats=[date_fmt]),
              help='Earliest date of requesting jobs (inclusive).')
@click.option('-b', '--created-before', type=click.DateTime(formats=[date_fmt]),
              help='Latest date of requesting jobs (inclusive).')
@click.option('-A', '--completed-after', type=click.DateTime(formats=[date_fmt]),
              help='Earliest date of completing jobs (inclusive).')
@click.option('-B', '--completed-before', type=click.DateTime(formats=[date_fmt]),
              help='Latest date of completing jobs (inclusive).')
@click.option('-n', '--name', type=str, help='Name of job(s).')
@click.option('-i', '--job-id', type=int, help='Id of a job.')
@click.option('-t', '--job-type', type=click.Choice(['routeanalysis', 'areaanalysis', 'trafficdensity']), multiple=True,
              help="The type of jobs.")
@click.option('-s', '--state', type=click.Choice([n.name for n in TomtomJobState]), multiple=True,
              help="The current state of jobs.")
def list_all_job_info(
    base_url: Optional[str] = None,
    version: Optional[int] = None,
    key: Optional[str] = None,
    page_index: Optional[int] = None,
    per_page: Optional[int] = None,
    created_after: Optional[dt.date] = None,
    created_before: Optional[dt.date] = None,
    completed_after: Optional[dt.date] = None,
    completed_before: Optional[dt.date] = None,
    name: Optional[str] = None,
    job_id: Optional[int] = None,
    job_type: Optional[List[str]] = None,
    state: Optional[List[str]] = None
) -> None:
    """Fetch information about the jobs registered."""
    state = [] if state is None else [TomtomJobState.from_str(s) for s in list(state)]
    job_type = [] if job_type is None else [TomtomReportType(t) for t in list(job_type)]

    client = TomtomClient(base_url=base_url, version=version, key=key)
    response = client.search_jobs(
        page_index=page_index,
        per_page=per_page,
        created_after=created_after,
        created_before=created_before,
        completed_after=completed_after,
        completed_before=completed_before,
        name=name,
        job_id=job_id,
        job_type=job_type,
        state=state
    )
    n = response.number_of_elements
    total = response.total_elements
    n_page = response.pageable.page_number + 1
    total_page = response.total_pages

    click.echo(f'The following jobs have been retrieved ({n}/{total} [p{n_page}/{total_page}]):')
    for job in response.content:
        info = job.display_info()
        click.echo(info)


@client.command
@click.option('-i', '--job-id', type=int, required=True,
              help='The job id for which the information needs to be fetched.')
@click.option('--base-url', type=str, required=False,
              help=f'Base URL for calling the API. (Default is env {config.env.base_url}')
@click.option('--version', type=int, required=False, help=f'The API version (Default is env {config.env.version})')
@click.option('--key', type=str, required=False, help=f'Your API key. (Default is env {config.env.key})')
def get_job_info(
    job_id: int,
    base_url: Optional[str] = None,
    version: Optional[int] = None,
    key: Optional[str] = None,
) -> None:
    """Display information about a specific job."""
    client = TomtomClient(base_url=base_url, version=version, key=key)
    response = client.status(job_id=job_id)
    click.echo(response.display_info())


@client.command
@click.option('--ip', type=str, required=False,
              help=f'The ip of the proxy server. (Default is env {config.env.proxy_ip}')
@click.option('--port', type=int, required=False,
              help=f'The port of the proxy server. (Default is env {config.env.proxy_port}')
@click.option('-u', '--username', type=str, required=False,
              help=f'The auth username for the proxy server. (Default is env {config.env.proxy_username}')
@click.option('-p', '--password', type=str, required=False,
              help=f'The auth password for the proxy server. (Default is env {config.env.proxy_password}')
@click.option('--base-url', type=str, required=False,
              help=f'Base URL for calling the API. (Default is env {config.env.base_url}')
@click.option('--version', type=int, required=False, help=f'The API version (Default is env {config.env.version})')
@click.option('--key', type=str, required=False, help=f'Your API key. (Default is env {config.env.key})')
def proxy_check(base_url, version, key, ip, port, username, password):
    """Get your ip with and without the configured proxy.
    The queries won't be performed if the proxy configuration is not well setup."""
    client = TomtomClient(base_url, version, key, ip, port, username, password)

    if client.proxy_url is None:
        click.echo('The proxy setup is not good.')
        exit(0)

    response_no_proxy = client.check_ip(False)
    response_proxy = client.check_ip(True)
    click.echo(f'w/o proxy:\t{response_no_proxy.ip}')
    click.echo(f'w/ proxy:\t{response_proxy.ip}')


# </editor-fold>

#
# ENV CLI
#
# <editor-fold desc="ENV">

@click.group()
def env():
    pass


@env.command
def list_env():
    """List the configurable environment variables."""
    click.echo('The available environment variables are:')
    click.echo('\n'.join([f'\t- {n}' for n in config.env.__dict__.values()]))
# </editor-fold>
