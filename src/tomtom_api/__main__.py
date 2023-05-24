from sys import exit

import click

from tomtom_api.cli import client, env
from tomtom_api.priority_queue.cli import queue

cli = click.CommandCollection(
    sources=[client, env, queue],
    context_settings={'help_option_names': ['-h', '--help']}
)


# the __name__ == 'tomtom_api.__main__' allows the creation of a custom command
if __name__ == '__main__' or __name__ == 'tomtom_api.__main__':
    cli()

exit(0)
