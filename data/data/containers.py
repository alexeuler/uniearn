import os
import logging.config
from typing import TypedDict
from dependency_injector import containers, providers
from ethereal import load_provider_from_uri, Ethereal
from web3 import Web3
from .keys import Keys
from .contracts import Contracts
from .executor import Executor
from .cache import Cache, MemoryCache, DbCache
from .worker import Worker

current_folder = os.path.realpath(os.path.dirname(__file__))


class EtherealConfig(TypedDict):
    rpc: str


def init_ethereal(config: EtherealConfig):
    w3 = Web3(load_provider_from_uri(config["rpc"]))
    return Ethereal(w3)


class AppContainer(containers.DeclarativeContainer):
    """
    The dependency injection container for Ethereal
    """

    config = providers.Configuration(
        yaml_files=[os.path.abspath(f"{current_folder}/../config.yml")]
    )
    logging = providers.Resource(logging.config.dictConfig, config=config.logging)
