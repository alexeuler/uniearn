import os
import json
from datetime import datetime
from itertools import islice

current_folder = os.path.realpath(os.path.dirname(__file__))
TOKEN_BLACKLIST = ["FEI", "CVX"]
FORCE_WHITELIST_POOLS = ["0x2e4784446a0a06df3d1a040b03e1680ee266c35a"]


class Pools:
    _data: dict = None
    _timestamp: int = None

    def length(
        self,
        token_filter: str | None = None,
        chain_filter: str | None = None,
        fees_filter: str | None = None,
    ):
        return len([*self._filter_data(token_filter, chain_filter, fees_filter)])

    def entities(
        self,
        skip: int = 0,
        limit: int = 20,
        token_filter: str | None = None,
        chain_filter: str | None = None,
        fees_filter: str | None = None,
        order_by: str | None = None,
        order: str | None = None,
    ):
        return list(
            islice(
                self._filter_data(
                    token_filter, chain_filter, fees_filter, order_by, order
                ),
                skip,
                skip + limit,
            )
        )

    def last_updated(self) -> int | None:
        file_path = os.path.join(
            current_folder, "fetched_data", "uniswap_pools_gql.json"
        )

        if os.path.exists(file_path):
            return int(os.path.getmtime(file_path) * 1000)

        return None

    def _filter_data(
        self,
        token_filter: str | None,
        chain_filter: str | None,
        fees_filter: str | None = None,
        order_by: str | None = None,
        order: str | None = None,
    ):
        data = self.data
        reverse = not order is None and order.lower() == "desc"
        if not order_by is None:
            data = sorted(
                self.data,
                key=lambda x: x[order_by],
                reverse=reverse,
            )
        return (
            self.strip_item(item)
            for item in data
            if self._filter_item(item, token_filter, chain_filter, fees_filter)
        )

    def _filter_item(
        self,
        item,
        token_filter: str | None,
        chain_filter: str | None,
        fees_filter: str | None = None,
    ):
        if (
            item["token0"].upper() in TOKEN_BLACKLIST
            or item["token1"].upper() in TOKEN_BLACKLIST
        ):
            if not item["id"].lower() in FORCE_WHITELIST_POOLS:
                return False

        if not token_filter is None:
            if (
                not token_filter.lower() == item["token0"].lower()
                and not token_filter.lower() == item["token1"].lower()
            ):
                return False

        if not chain_filter is None:
            if int(chain_filter) != item["chainId"]:
                return False
        if not fees_filter is None:
            if item["last_month_fees"] < int(fees_filter):
                return False
        return True

    def strip_item(self, item):
        keys = [
            "id",
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
            "last_month_fees",
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
