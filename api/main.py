from fastapi import FastAPI, Depends
import json
import os
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from gql import gql
from containers import AppContainer
from gql_client import GQLClient
from pools import Pools
from ethereal_provider import EtherealProvider
from dependency_injector.wiring import Provide, inject
from ethereal import Ethereal
from web3.contract import Contract

app = FastAPI()
origins = ["*"]
current_folder = os.path.realpath(os.path.dirname(__file__))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

container = AppContainer()


@app.on_event("startup")
def configure_dependency_injector():
    container.config.from_yaml("config.yaml")
    container.wire(modules=[__name__])


@app.get("/pools")
@inject
async def pools(
    skip: int = 0,
    limit: int = 10,
    token_filter: str | None = None,
    chain_filter: str | None = None,
    fees_filter: str | None = None,
    order_by: str | None = None,
    order: str | None = None,
    pools_data: Pools = Depends(Provide[AppContainer.pools]),
):
    return {
        "pools": pools_data.entities(
            skip, limit, token_filter, chain_filter, fees_filter, order_by, order
        ),
        "last_updated": pools_data.last_updated(),
    }


@app.get("/pools/{address}")
@inject
async def pools(
    address: str,
    chain_id: int = 1,
    pools_data: Pools = Depends(Provide[AppContainer.pools]),
):
    return pools_data.entity(address, chain_id)


@app.get("/pools_count")
@inject
async def pools_count(
    token_filter: str | None = None,
    chain_filter: str | None = None,
    fees_filter: str | None = None,
    pools_data: Pools = Depends(Provide[AppContainer.pools]),
):
    return {
        "total": pools_data.length(token_filter, chain_filter, fees_filter),
    }


@app.get("/pools/{token0}/{token1}/{fee_tier}")
@inject
async def pools(
    token0: str,
    token1: str,
    fee_tier: int,
    chain_id: int = 1,
    graphql: GQLClient = Depends(Provide[AppContainer.gql_client]),
):
    token0, token1 = sorted([token0.lower(), token1.lower()])
    print(token0, token1, fee_tier)
    query = gql(
        """
        query Q {
            pools(where:{token0:"%s", token1:"%s", feeTier: %s}) {
                address: id
                tick
                sqrtPrice
                liquidity
                token0 {
                    address: id
                    name
                    symbol
                    decimals
                }
                token1 {
                    address: id
                    name
                    symbol
                    decimals
                }
                feeTier
            }
        }
        """
        % (token0, token1, fee_tier)
    )
    resp = await graphql.request(query, chain_id)
    if len(resp["pools"]) == 0:
        return None
    pool = resp["pools"][0]
    pool["address"] = pool["address"].lower()
    pool["token0"]["address"] = pool["token0"]["address"].lower()
    pool["token0"]["decimals"] = int(pool["token0"]["decimals"])
    pool["token1"]["address"] = pool["token1"]["address"].lower()
    pool["token1"]["decimals"] = int(pool["token1"]["decimals"])
    pool["feeTier"] = int(pool["feeTier"])
    pool["tick"] = int(pool["tick"])
    return pool


@app.get("/positions/{address}")
@inject
async def positions(
    address: str,
    chain_id: int = 1,
    graphql: GQLClient = Depends(Provide[AppContainer.gql_client]),
):
    query = gql(
        """
        query Q {
            positions(where:{owner:"%s"}) {
                id
                owner
                liquidity
                pool {
                    id
                    sqrtPrice
                    tick
                    token0 {
                        address: id
                        name
                        symbol
                        decimals
                    }
                    token1 {
                        address: id
                        name
                        symbol
                        decimals
                    }
                    feeTier
                }
                tickLower {
                    id
                    tickIdx
                }
                tickUpper {
                    id
                    tickIdx
                }
            }
        }
        """
        % (address)
    )

    res = await graphql.request(query, chain_id)
    for pos in res["positions"]:
        update_position_types(pos)
    return res


@app.get("/nfts/{id}")
@inject
async def position(
    id: int,
    chain_id: int = 1,
    graphql: GQLClient = Depends(Provide[AppContainer.gql_client]),
    ethereal_provider: EtherealProvider = Depends(
        Provide[AppContainer.ethereal_provider]
    ),
):
    if chain_id == 42161:
        return await get_arbitrum_nft(id, graphql, ethereal_provider, chain_id)
    return await get_normal_nft(id, graphql, chain_id)


@app.get("/ticks/{pool_address}")
@inject
async def ticks(
    pool_address: str,
    offset: int = 0,
    limit: int = 100,
    chain_id: int = 1,
    graphql: GQLClient = Depends(Provide[AppContainer.gql_client]),
):
    tasks = []
    for i in range(0, limit, 1000):
        tasks.append(
            get_ticks_chunk(
                pool_address, offset + i, min(1000, limit - i), chain_id, graphql
            )
        )
    results = await asyncio.gather(*tasks)
    return {
        "ticks": [
            {"tick": int(tick["tickIdx"]), "liquidity_net": tick["liquidityNet"]}
            for result in results
            for tick in result["ticks"]
        ]
    }


@app.get("/aave/tokens")
async def aave_tokens(chain_id: int = 1):
    contract = aave_data_provider(chain_id)
    aTokens = contract.functions.getAllATokens().call()
    tokens = contract.functions.getAllReservesTokens().call()
    return {
        "tokens": [{"symbol": t[0], "address": t[1]} for t in tokens],
        "aTokens": [{"symbol": t[0], "address": t[1]} for t in aTokens],
    }


def _enrich_aave_tokens(ethereal: Ethereal, tokens):
    return [
        {
            "symbol": t["symbol"],
            "address": t["address"],
            "decimals": t["decimals"],
            "name": t["name"],
        }
        for t in tokens
    ]


@app.get("/aave/tokens/{token_address}/user_reserves/{address}")
@inject
async def aave_tokens(
    token_address: str,
    address: str,
    chain_id: int = 1,
    ethereal_provider: EtherealProvider = Depends(
        Provide[AppContainer.ethereal_provider]
    ),
):
    ethereal = ethereal_provider.get(chain_id)
    contract = aave_data_provider(ethereal, chain_id)
    try:
        resp = contract.functions.getUserReserveData(
            ethereal.to_checksum_address(token_address),
            ethereal.to_checksum_address(address),
        ).call()
        return {
            "currentATokenBalance": resp[0],
            "currentStableDebt": resp[1],
            "currentVariableDebt": resp[2],
            "principalStableDebt": resp[3],
            "scaledVariableDebt": resp[4],
            "stableBorrowRate": resp[5],
            "liquidityRate": resp[6],
            "stableRateLastUpdated": resp[7],
            "usageAsCollateralEnabled": resp[8],
        }
    except Exception as e:
        return None


@app.get("/aave/tokens/{token_address}/price_usd")
@inject
async def aave_token_price(
    token_address: str,
    chain_id: int = 1,
    ethereal_provider: EtherealProvider = Depends(
        Provide[AppContainer.ethereal_provider]
    ),
):
    ethereal = ethereal_provider.get(chain_id)
    address_provider = aave_address_provider(ethereal, chain_id)

    try:
        oracle_address = address_provider.functions.getPriceOracle().call()
        oracle = aave_price_oracle(ethereal, oracle_address)
        price = oracle.functions.getAssetPrice(
            ethereal.to_checksum_address(token_address)
        ).call()
        price /= 10**8

        return {"price": price}
    except Exception as e:
        return None


@app.get("/aave/reserves/config/{token_address}")
@inject
async def aave_token_reserves_config(
    token_address: str,
    chain_id: int = 1,
    ethereal_provider: EtherealProvider = Depends(
        Provide[AppContainer.ethereal_provider]
    ),
):
    ethereal = ethereal_provider.get(chain_id)
    contract = aave_data_provider(ethereal, chain_id)
    try:
        resp = contract.functions.getReserveConfigurationData(
            ethereal.to_checksum_address(token_address),
        ).call()
        return {
            "decimals": resp[0],
            "ltv": resp[1],
            "liquidationThreshold": resp[2],
            "liquidationBonus": resp[3],
            "reserveFactor": resp[4],
            "usageAsCollateralEnabled": resp[5],
            "borrowingEnabled": resp[6],
            "stableBorrowRateEnabled": resp[7],
            "isActive": resp[8],
            "isFrozen": resp[9],
        }
    except Exception as e:
        return None


async def get_ticks_chunk(
    pool_address: str, offset: int, limit: int, chain_id: int, graphql: GQLClient
):
    query = gql(
        """
            query Q {
                ticks(where: {poolAddress: "%s"}, orderBy: tickIdx, skip: %s, first: %s) {
                    tickIdx
                    liquidityNet
                }
            }
        """
        % (pool_address, offset, limit)
    )
    res = await graphql.request(query, chain_id)
    return res


async def get_normal_nft(id: int, graphql: GQLClient, chain_id: int):
    query = gql(
        """
        query Q {
            position(id:%s) {
                id
                owner
                liquidity
                pool {
                    id
                    sqrtPrice
                    tick
                    token0 {
                        address: id
                        name
                        symbol
                        decimals
                    }
                    token1 {
                        address: id
                        name
                        symbol
                        decimals
                    }
                    feeTier
                }
                tickLower {
                    tickIdx
                }
                tickUpper {
                    tickIdx
                }
            }
        }
        """
        % (id)
    )
    res = await graphql.request(query, chain_id)
    update_position_types(res["position"])
    return res


async def get_arbitrum_nft(
    id: int, graphql: GQLClient, ethereal_provider: EtherealProvider, chain_id: int
):
    ethereal = ethereal_provider.get(chain_id)
    with open(f"{current_folder}/abi/nonfungible_position_manager.json") as f:
        contract = ethereal.eth.contract(
            "0xC36442b4a4522E871399CD717aBDD847Ab11FE88", abi=json.load(f)
        )
    (
        _,
        _,
        token0,
        token1,
        fee,
        tick_lower,
        tick_upper,
        liquidity,
        _,
        _,
        _,
        _,
    ) = contract.functions.positions(id).call()
    owner = contract.functions.ownerOf(id).call()
    query = gql(
        """
        query Q {
            pools(
                where: {token0: "%s", token1: "%s", feeTier: %s}
            ) {
                id
                sqrtPrice
                tick
                token0 {
                    name
                    symbol
                    decimals
                }
                token1 {
                    name
                    symbol
                    decimals
                }
                feeTier
            }
        }        
        """
        % (token0.lower(), token1.lower(), fee)
    )
    pools = await graphql.request(query, chain_id)
    res = {
        "id": id,
        "owner": owner,
        "liquidity": str(int(liquidity)),
        "pool": pools["pools"][0],
        "tickLower": {"tickIdx": tick_lower},
        "tickUpper": {"tickIdx": tick_upper},
    }
    update_position_types(res)
    return res


def update_position_types(pos: dict):
    pos["id"] = int(pos["id"])
    pos["pool"]["feeTier"] = int(pos["pool"]["feeTier"])
    pos["pool"]["tick"] = int(pos["pool"]["tick"]) if pos["pool"]["tick"] else None
    pos["pool"]["token0"]["decimals"] = int(pos["pool"]["token0"]["decimals"])
    pos["pool"]["token1"]["decimals"] = int(pos["pool"]["token1"]["decimals"])
    pos["tickLower"]["tickIdx"] = int(pos["tickLower"]["tickIdx"])
    # pos["tickLower"]["price0"] = float(pos["tickLower"]["price0"])
    # pos["tickLower"]["price1"] = float(pos["tickLower"]["price1"])
    pos["tickUpper"]["tickIdx"] = int(pos["tickUpper"]["tickIdx"])
    # pos["tickUpper"]["price0"] = float(pos["tickUpper"]["price0"])
    # pos["tickUpper"]["price1"] = float(pos["tickUpper"]["price1"])


@inject
def aave_data_provider(
    ethereal: Ethereal,
    chain_id: int = 1,
    config=Provide[AppContainer.config],
) -> Contract:
    with open(f"{current_folder}/abi/protocol_data_provider.json") as f:
        return ethereal.eth.contract(
            ethereal.to_checksum_address(
                config["aave"]["contracts"]["protocol_data_provider"][chain_id]
            ),
            abi=json.load(f),
        )


@inject
def aave_address_provider(
    ethereal: Ethereal,
    chain_id: int = 1,
    config=Provide[AppContainer.config],
) -> Contract:
    with open(f"{current_folder}/abi/address_provider.json") as f:
        return ethereal.eth.contract(
            ethereal.to_checksum_address(
                config["aave"]["contracts"]["address_provider"][chain_id]
            ),
            abi=json.load(f),
        )


def aave_price_oracle(
    ethereal: Ethereal,
    address: str,
) -> Contract:
    with open(f"{current_folder}/abi/aave_oracle.json") as f:
        return ethereal.eth.contract(
            ethereal.to_checksum_address(address),
            abi=json.load(f),
        )
