from typing import Dict, TypedDict
from functools import cache
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from .base import Base


class UniswapConfig(TypedDict):
    graphql: Dict[int, str]


class Uniswap(Base):
    _config: UniswapConfig

    def __init__(self, config: UniswapConfig, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config = config

    def get_pools(
        self,
        first: int,
        skip: int,
        symbol: str,
        chain_id: int,
        min_fees_usd: int,
        pool_data_days: int,
    ):
        query = gql(
            """
        query Q {
            pools(
                first: %s
                skip: %s
                orderBy: feesUSD
                orderDirection: desc
                where: {feesUSD_gt: %s, token0_: {symbol_in: ["%s"]} }
            ) {
                id
                token0 {
                id
                name
                symbol
                decimals
                }
                token1 {
                id
                name
                symbol
                decimals
                }
                feeTier
                liquidity
                sqrtPrice
                token0Price
                token1Price
                totalValueLockedUSD
                volumeUSD
                feesUSD
                poolDayData(first: %s, orderBy:date, orderDirection: desc) {
                    date
                    sqrtPrice
                }
            }
        }
        """
            % (first, skip, min_fees_usd, symbol, pool_data_days)
        )
        client = self._client(chain_id)
        return client.execute(query)

    @cache
    def _client(self, chain_id: int) -> Client:
        transport = RequestsHTTPTransport(url=self._config["graphql"][chain_id])
        return Client(transport=transport, fetch_schema_from_transport=True)
