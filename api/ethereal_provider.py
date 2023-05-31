from functools import cache
from base import Base
from ethereal import Ethereal
from web3 import Web3


class EtherealProvider(Base):
    _ethereal_config: dict

    def __init__(self, ethereal_config: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ethereal_config = ethereal_config

    @cache
    def get(self, chain_id: int) -> Ethereal:
        web3 = Web3(Web3.HTTPProvider(self._ethereal_config["rpc"][chain_id]))
        return Ethereal(web3)
