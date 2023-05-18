from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from data import Pools

app = FastAPI()
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pools_data = Pools()


@app.get("/pools")
async def pools(
    skip: int = 0,
    limit: int = 10,
    token_filter: str | None = None,
    chain_filter: str | None = None,
    fees_filter: str | None = None,
    order_by: str | None = None,
    order: str | None = None,
):
    return {
        "pools": pools_data.entities(
            skip, limit, token_filter, chain_filter, fees_filter, order_by, order
        ),
        "last_updated": pools_data.last_updated(),
    }


@app.get("/pools_count")
async def pools(
    token_filter: str | None = None,
    chain_filter: str | None = None,
    fees_filter: str | None = None,
):
    return {
        "total": pools_data.length(token_filter, chain_filter, fees_filter),
    }
