import os
from typing import Dict, TypedDict
from functools import cache
import json
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from .base import Base

current_folder = os.path.realpath(os.path.dirname(__file__))
print(current_folder)


class UniswapConfig(TypedDict):
    graphql: Dict[int, str]
    min_fees_usd: Dict[int, int]


class Uniswap(Base):
    _config: UniswapConfig

    def __init__(self, config: UniswapConfig, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config = config

    @property
    def pools_local_path(self):
        return os.path.join(current_folder, "fetched_data", "uniswap_pools_gql.json")

    def fetch_all_pools(self, symbol: str):
        res = []
        for chain_id in self._config["graphql"].keys():
            chain_id = int(chain_id)
            min_fees = int(self._config["min_fees_usd"][chain_id])
            resp = self.get_all_pools_for_chain(symbol, chain_id, min_fees)
            for item in resp:
                item["chainId"] = chain_id
            res += resp
        with open(
            self.pools_local_path,
            "w",
        ) as f:
            json.dump(res, f, indent=4, sort_keys=True)
        return res

    def get_all_pools_for_chain(self, symbol: str, chain_id: int, min_fees_usd: int):
        first = 50
        length = first
        skip = 0
        pools = []
        while length == first:
            response = self.get_pools(first, skip, symbol, chain_id, min_fees_usd, 30)
            pools += response
            length = len(response)
            skip += length
        return pools

    def get_pools(
        self,
        first: int,
        skip: int,
        symbol: str,
        chain_id: int,
        min_fees_usd: int,
        pool_data_days: int,
    ):
        self.logger.debug(
            f"Querying Uniswap for pools for {symbol} at chain {chain_id} starting at {skip} with length {first}, min_fees: {min_fees_usd}, pool_data_days: {pool_data_days}"
        )
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
        reties = 3
        while True:
            try:
                return client.execute(query)["pools"]
            except Exception as e:
                self.logger.debug(f"Error: {e}, retries left {reties}")
                reties -= 1
                if reties == 0:
                    raise e

    @cache
    def _client(self, chain_id: int) -> Client:
        transport = RequestsHTTPTransport(url=self._config["graphql"][chain_id])
        return Client(transport=transport, fetch_schema_from_transport=True)
