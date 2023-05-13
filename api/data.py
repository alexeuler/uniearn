import os
import json
from datetime import datetime
from itertools import islice

current_folder = os.path.realpath(os.path.dirname(__file__))


class Pools:
    _data: dict = None
    _timestamp: int = None

    def length(self, token: str):
        return len([*self._filter_data(token)])

    def entities(self, skip: int = 0, limit: int = 20, token: str | None = None):
        return list(islice(self._filter_data(token), skip, skip + limit))

    def _filter_data(self, token: str | None):
        if token is None:
            return (self.strip_item(i) for i in self.data)
        token = token.lower()
        return (
            self.strip_item(item)
            for item in self.data
            if token in item["token0"].lower() or token in item["token1"].lower()
        )

    def strip_item(self, item):
        keys = [
            "token0",
            "token1",
            "feeTier",
            "chainId",
            "annualized_price_volatility",
            "liquidity",
            "avg_liquidity",
            "price",
            "tvl_usd",
            "normalized_tvl_usd",
            "return",
            "normalized_return",
            "risk",
            "sharpe",
        ]
        res = {k: item[k] for k in keys}
        return res

    @property
    def data(self):
        now = datetime.now().timestamp()
        if self._timestamp and now - self._timestamp < 1 * 60:
            return self._data

        path = os.path.join(current_folder, "fetched_data", "uniswap_pools.json")
        timestamp = os.stat(path).st_birthtime
        if timestamp != self._timestamp:
            with open(path, "r") as f:
                self._data = json.load(f)
            self._timestamp = timestamp
        return self._data
