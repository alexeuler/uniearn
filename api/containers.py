import os
import logging.config
from typing import TypedDict
from dependency_injector import containers, providers
from pools import Pools
from ethereal_provider import EtherealProvider
from gql_client import GQLClient

current_folder = os.path.realpath(os.path.dirname(__file__))


class EtherealConfig(TypedDict):
    rpc: str


class AppContainer(containers.DeclarativeContainer):
    """
    The dependency injection container for Ethereal
    """

    config = providers.Configuration(
        yaml_files=[os.path.abspath(f"{current_folder}/config.yml")]
    )
    logging = providers.Resource(logging.config.dictConfig, config=config.logging)
    gql_client = providers.Singleton(GQLClient, uniswap_config=config.uniswap)
    ethereal_provider = providers.Singleton(
        EtherealProvider, ethereal_config=config.ethereal
    )
    pools = providers.Singleton(Pools)
