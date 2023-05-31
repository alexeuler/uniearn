from fastapi import FastAPI, Depends
import json
import os
from fastapi.middleware.cors import CORSMiddleware
from gql import gql
from containers import AppContainer
from gql_client import GQLClient
from pools import Pools
from ethereal_provider import EtherealProvider
from dependency_injector.wiring import Provide, inject

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
    print(contract.functions.positions(id).call())
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
        "pool": pools["pools"][0],
        "liquidity": str(int(liquidity)),
        "tickLower": {"tickIdx": tick_lower},
        "tickUpper": {"tickIdx": tick_upper},
    }
    update_position_types(res)
    return res


def update_position_types(pos: dict):
    pos["id"] = int(pos["id"])
    pos["pool"]["feeTier"] = int(pos["pool"]["feeTier"])
    pos["pool"]["tick"] = int(pos["pool"]["tick"])
    pos["pool"]["token0"]["decimals"] = int(pos["pool"]["token0"]["decimals"])
    pos["tickLower"]["tickIdx"] = int(pos["tickLower"]["tickIdx"])
    # pos["tickLower"]["price0"] = float(pos["tickLower"]["price0"])
    # pos["tickLower"]["price1"] = float(pos["tickLower"]["price1"])
    pos["tickUpper"]["tickIdx"] = int(pos["tickUpper"]["tickIdx"])
    # pos["tickUpper"]["price0"] = float(pos["tickUpper"]["price0"])
    # pos["tickUpper"]["price1"] = float(pos["tickUpper"]["price1"])
