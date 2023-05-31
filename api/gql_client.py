from functools import cache
import backoff
import asyncio
from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport

# from gql.transport.requests import RequestsHTTPTransport
from base import Base


class GraphQLEngineClient(Base):
    _url: str

    def __init__(self, url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._url = url
        self._client = Client(
            transport=AIOHTTPTransport(url=url),
            fetch_schema_from_transport=True,
        )
        self._session = None
        self._connect_task = None
        self._close_event = asyncio.Event()

    @backoff.on_exception(backoff.expo, Exception, max_time=300)
    async def _connection(self):
        self.logger.debug(f"Connecting to {self._url}")

        try:
            async with self._client as session:
                self._session = session
                self.logger.debug(f"Connected to {self._url}")

                # Wait for the close event
                self._close_event.clear()
                await self._close_event.wait()

                self._session = None
                self._connect_task = None

                self.logger.debug(f"Closed {self._url}")
                return

        finally:
            self._session = None
            self._connect_task = None
            self.logger.debug(f"Disconnected {self._url}")

    def connect(self):
        if not self._connect_task:
            self._connect_task = asyncio.create_task(self._connection())

    def close(self):
        self._close_event.set()

    async def execute(self, document):
        retries = 3
        while True:
            if not self._session:
                self.connect()
                retries -= 1
                if retries == 0:
                    raise Exception("Not connected")
                await asyncio.sleep(1)
                continue

            try:
                return await self._session.execute(document)
            except Exception as e:
                self.logger.debug(f"Error: {e}, retries left {retries}")
                retries -= 1
                if retries == 0:
                    raise e


class GQLClient(Base):
    _uniswap_config: dict

    def __init__(self, uniswap_config: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._uniswap_config = uniswap_config

    async def request(self, query: str, chain_id: int):
        return await self.client(chain_id).execute(query)

    @cache
    def client(self, chain_id: int) -> GraphQLEngineClient:
        return GraphQLEngineClient(self._uniswap_config["graphql"][chain_id])
