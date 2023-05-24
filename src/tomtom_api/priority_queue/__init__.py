"""Priority queue for tomtom jobs

Since the TOMTOM API does not provide this feature, this module allows the users to give a priority order to the
jobs that need to be submitted to the TOMTOM move api.

The tomtom jobs are submitted to this module instead of directly being sent to Tomtom.
A daemon is then responsible for constantly looking if it's possible to submit a new job on tomtom.

The daemon can be launched with `tomtom-daemon start`.

Interaction with this module is available through
    * a code API (in `tomtom_api.priority_queue.lib`)
    * a CLI (you can list the available command with `tomtom-api --help | grep queue`)

The higher the priority is, the more priority has the job.

The database is a parquet file located in the `TomtomEnvironmentVariables.home_folder` environment variable.
"""
