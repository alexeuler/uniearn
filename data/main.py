import os
import click
import json
from dependency_injector.wiring import inject, Provide
from data.containers import AppContainer
from data.uniswap import Uniswap


current_folder = os.path.realpath(os.path.dirname(__file__))


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
    Data CLI
    """

    app = AppContainer()
    app.config.core.logging.loggers["root"].level.from_value(log_level)
    app.config.ethereal.rpc.from_value(rpc)
    app.init_resources()
    app.wire(modules=[__name__])


@cli.command()
@inject
def fetch_pools(
    uniswap: Uniswap = Provide[AppContainer.uniswap],
):
    """
    Get all pools

    """
    res = uniswap.fetch_all_pools()
    print(json.dumps(res, indent=4, sort_keys=True))


@cli.command()
@inject
def process_pools(
    uniswap: Uniswap = Provide[AppContainer.uniswap],
):
    """
    Process all pools

    """
    res = uniswap.process_pools()
    print(json.dumps(res, indent=4, sort_keys=True))


@cli.command()
@click.option("--first", type=int, default=10, help="The number of pools to return")
@click.option("--skip", type=int, default=0, help="The number of pools to skip")
@click.option("--chain_id", type=int, default=1, help="The chain id to use")
@click.option(
    "--min_fees_usd", type=int, default=100_000, help="The minimum fees in USD"
)
@click.option(
    "--pool_data_days",
    type=int,
    default=30,
    help="The number of days of pool data to return",
)
@inject
def pool(
    first: int,
    skip: int,
    chain_id: int,
    min_fees_usd: int,
    pool_data_days: int,
    uniswap: Uniswap = Provide[AppContainer.uniswap],
):
    """
    Get pools

    """
    res = uniswap.get_pools(first, skip, chain_id, min_fees_usd, pool_data_days)
    print(json.dumps(res, indent=4, sort_keys=True))


def start_cli():
    """
    Start the CLI
    """
    # pylint: disable=no-value-for-parameter
    cli(auto_envvar_prefix="UNIEARN_DATA")


if __name__ == "__main__":
    start_cli()
