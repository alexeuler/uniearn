import os
import pprint
import json
import click
from web3 import Web3
from dependency_injector.wiring import inject, Provide
from airdrop.containers import AppContainer
from airdrop.keys import Keys
from airdrop.contracts import Contracts
from airdrop.executor import Executor
from airdrop.worker import Worker


current_folder = os.path.realpath(os.path.dirname(__file__))


def parse_keys(keys_prompt: str) -> list[int]:
    if keys_prompt.find("-") == -1:
        return [int(i) for i in keys_prompt.split(",")]
    from_key, to_key = keys_prompt.split("-")
    from_key, to_key = int(from_key), int(to_key)
    return [from_key + i for i in range(to_key - from_key + 1)]


@click.group()
@click.option(
    "-ll",
    "--log-level",
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    default="INFO",
    help="Log level for the app",
)
@click.option(
    "-r",
    "--rpc",
    type=str,
    default=lambda: os.environ.get("WEB3_PROVIDER_URI", "http://localhost:8545"),
    help="RPC endpoint to use",
)
def cli(log_level: str | None, rpc: str | None):
    """
    Ethereal CLI
    """

    app = AppContainer()
    app.config.core.logging.loggers["root"].level.from_value(log_level)
    app.config.ethereal.rpc.from_value(rpc)
    app.init_resources()
    app.wire(modules=[__name__])


@cli.command()
@inject
def seed(
    keys: Keys = Provide[AppContainer.keys],
):
    """
    Print seed phrase
    """

    print(keys.seed)


@cli.command()
@click.argument("index", type=str)
@inject
def key(
    index: str,
    keys: Keys = Provide[AppContainer.keys],
):
    """
    Print key

    :param index: Index of the key
    """
    ks = parse_keys(index)
    key_data = [keys[idx] for idx in ks]
    pprint.pprint(key_data)


@cli.command()
@click.argument("name", type=str)
@inject
def contract(
    name: str,
    contracts: Contracts = Provide[AppContainer.contracts],
):
    """
    Print contract address

    :param name: Name of the contract
    """

    print(getattr(contracts, name).address)


@cli.command()
@click.argument("from_key", type=int)
@click.argument("to_keys", type=str)
@click.argument("amount", type=float)
@inject
def disperse_eth(
    from_key: int,
    to_keys: str,
    amount: float,
    executor: Executor = Provide[AppContainer.executor],
):
    """
    Disperse ETH from one key to many keys

    :param from_key: Index of the key to disperse from
    :param to_keys: Index of the keys to disperse to (1-3, or 4,8,10)
    :param amount: Amount of ETH to disperse
    """
    keys = parse_keys(to_keys)
    executor.disperse_eth(from_key, keys, int(amount * 1e18))


@cli.command()
@click.argument("from_key", type=int)
@click.argument("amount", type=float)
@inject
def mute_swap_eth(
    from_key: int,
    amount: float,
    executor: Executor = Provide[AppContainer.executor],
):
    executor.mute_swap_eth(from_key, int(amount * 1e18))


@cli.command()
@click.argument("from_key", type=int)
@click.argument("amount", type=float)
@inject
def mute_swap_usdc(
    from_key: int,
    amount: float,
    executor: Executor = Provide[AppContainer.executor],
):
    executor.mute_swap_usdc(from_key, int(amount * 1e6))


@cli.command()
@click.argument("key", type=int)
@inject
def step(
    key: int,
    executor: Executor = Provide[AppContainer.executor],
):
    executor.step(key)


@cli.command()
@click.argument("keys", type=str)
@inject
def nonces(
    keys: str,
    worker: Worker = Provide[AppContainer.worker],
):
    """
    Display nonces

    :param keys: Keys to use
    """
    parsed_keys = parse_keys(keys)
    pprint.pprint(worker.nonces(parsed_keys))


@cli.command()
@click.argument("keys", type=str)
@click.argument("frequency", type=float)
@inject
def start(
    keys: str,
    frequency: float,
    worker: Worker = Provide[AppContainer.worker],
):
    """
    Start the worker

    :param keys: Keys to use
    :param frequency: Frequency the key will issue transactions (how many days between each transaction)
    """
    parsed_keys = parse_keys(keys)
    worker.run(parsed_keys, frequency)


def start_cli():
    """
    Start the CLI
    """
    # pylint: disable=no-value-for-parameter
    cli(auto_envvar_prefix="ARKENSTONE_AIRDROP")


if __name__ == "__main__":
    start_cli()
