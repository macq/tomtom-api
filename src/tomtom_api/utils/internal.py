"""Internal module
Mainly used for generating the configuration and logger objects.

The name of the environment variables are defined here (See `TomtomEnvironmentVariables`)
"""
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


@dataclass
class TomtomEnvironmentVariables:
    base_url: str = 'TOMTOM_API_BASE_URL'
    key: str = 'TOMTOM_API_KEY'
    version: str = 'TOMTOM_API_VERSION'
    log_level: str = 'TOMTOM_API_LOG_LEVEL'
    tmp_folder: str = 'TOMTOM_API_TMP_FOLDER'
    proxy_ip: str = 'TOMTOM_API_PROXY_IP'
    proxy_port: str = 'TOMTOM_API_PROXY_PORT'
    proxy_username: str = 'TOMTOM_API_PROXY_USERNAME'
    proxy_password: str = 'TOMTOM_API_PROXY_PASSWORD'
    home_folder: str = 'TOMTOM_API_HOME_FOLDER'
    queue_loop_duration: str = 'TOMTOM_API_QUEUE_LOOP_DURATION'


@dataclass
class TomtomLogging:
    level: str


@dataclass
class TomtomProxy:
    ip: str
    port: int
    username: str
    password: str


@dataclass
class TomtomApi:
    base_url: str
    version: int
    key: str
    proxy: TomtomProxy


@dataclass
class TomtomPath:
    tmp: Path
    home: Path


@dataclass
class TomtomQueue:
    loop_duration: int  # loop interval in seconds


@dataclass
class TomtomConfig:
    env: TomtomEnvironmentVariables
    log: TomtomLogging
    api: TomtomApi
    path: TomtomPath
    queue: TomtomQueue


def init_config_and_logger() -> Tuple[TomtomConfig, logging.Logger]:
    environment_variables = TomtomEnvironmentVariables()
    env_proxy_port = os.getenv(environment_variables.proxy_port)
    config = TomtomConfig(
        env=environment_variables,
        log=TomtomLogging(level=os.getenv(environment_variables.log_level, 'info').upper()),
        api=TomtomApi(
            base_url=os.getenv(environment_variables.base_url, 'api.tomtom.com'),
            version=int(os.getenv(environment_variables.version, 1)),
            key=os.getenv(environment_variables.key),
            proxy=TomtomProxy(
                ip=os.getenv(environment_variables.proxy_ip),
                port=None if env_proxy_port is None else int(env_proxy_port),
                username=os.getenv(environment_variables.proxy_username),
                password=os.getenv(environment_variables.proxy_password)
            )
        ),
        path=TomtomPath(tmp=Path(os.getenv(environment_variables.tmp_folder, '/tmp')),
                        home=Path(os.getenv(environment_variables.home_folder, Path.home() / '.tomtom-api'))),
        queue=TomtomQueue(loop_duration=int(os.getenv(environment_variables.queue_loop_duration, 60)))
    )

    logger = logging.getLogger('tomtom_api')
    if logger.handlers:
        return logger

    log_level = config.log.level
    fmt = "%(asctime)s %(name)s [%(levelname)s] %(message)s"

    formatter = logging.Formatter(fmt)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.setLevel(log_level)
    logger.addHandler(console_handler)

    return config, logger
