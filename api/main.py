from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from gql import gql
from containers import AppContainer
from gql_client import GQLClient
from pools import Pools
from dependency_injector.wiring import Provide, inject

app = FastAPI()
origins = ["*"]

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
                    price0
                    price1
                }
                tickUpper {
                    id
                    tickIdx
                    price0
                    price1
                }
            }
        }
        """
        % (address)
    )

    return await graphql.request(query, chain_id)
