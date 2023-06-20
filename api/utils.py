from typing import Any, Dict, Union
from hexbytes import HexBytes
from web3.contract.contract import (
    Contract,
    ContractEvent,
    ContractFunction,
)
from eth_utils import function_abi_to_4byte_selector
from web3._utils.abi import get_abi_input_types, get_abi_output_types
from web3 import Web3
import json
from ethereal import Ethereal
from eth_typing.encoding import HexStr
from web3.datastructures import AttributeDict
import os

current_folder = os.path.realpath(os.path.dirname(__file__))


class Web3JsonEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for Web3 objects.
    """

    def default(self, o: Any) -> Union[Dict[Any, Any], HexStr]:
        if isinstance(o, AttributeDict):
            return dict(o.items())
        if isinstance(o, HexBytes):
            return HexStr(o.hex())
        if isinstance(o, (bytes, bytearray)):
            return HexStr(HexBytes(o).hex())
        return json.JSONEncoder.default(self, o)


def json_response(response: AttributeDict) -> str:
    """
    Convert a Web3 response to JSON.
    """
    return json.dumps(response, cls=Web3JsonEncoder)


def calldata(call: ContractFunction) -> str:
    selector = HexBytes(function_abi_to_4byte_selector(call.abi)).hex()
    abi_types = get_abi_input_types(call.abi)
    bytes_calldata = call.w3.codec.encode(abi_types, call.args)
    return selector + HexBytes(bytes_calldata).hex()[2:]


def multicall(calls: list[ContractFunction]) -> list[str]:
    if len(calls) == 0:
        return []
    multicall = multicall_contract(calls[0].w3)
    addresses = [call.address for call in calls]
    calldatas = [calldata(call) for call in calls]
    args = [*zip(addresses, calldatas)]
    return json_response(multicall.functions.aggregate(args).call())


def multicall_contract(w3: Web3) -> Contract:
    with open(f"{current_folder}/abi/multicall.json") as f:
        abi = json.load(f)
        return w3.eth.contract("0xcA11bde05977b3631167028862bE2a173976CA11", abi=abi)


def erc20_contract(w3: Web3, address) -> Contract:
    with open(f"{current_folder}/abi/erc20.json") as f:
        abi = json.load(f)
        return w3.eth.contract(address, abi=abi)


# def erc20_data(w3: Web3, address):
#     contract = erc20_contract(w3, address)
#     return {
#         "address": address,
#         "name": erc20_contract(Ethereal.w3).functions.name().call(),
#         "symbol": erc20_contract(Ethereal.w3).functions.symbol().call(),
#         "decimals": erc20_contract(Ethereal.w3).functions.decimals().call(),
#     }
