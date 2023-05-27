from functools import cache
from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport

# from gql.transport.requests import RequestsHTTPTransport
from base import Base


class GQLClient(Base):
    _uniswap_config: dict

    def __init__(self, uniswap_config: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._uniswap_config = uniswap_config

    async def request(self, query: str, chain_id: int):
        client = self.client(chain_id)
        reties = 3
        while True:
            try:
                return await client.execute_async(query)
            except Exception as e:
                self.logger.debug(f"Error: {e}, retries left {reties}")
                reties -= 1
                if reties == 0:
                    raise e

    @cache
    def client(self, chain_id: int):
        transport = AIOHTTPTransport(url=self._uniswap_config["graphql"][chain_id])
        return Client(transport=transport, fetch_schema_from_transport=True)
