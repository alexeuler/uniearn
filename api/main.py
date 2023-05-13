from fastapi import FastAPI
from data import Pools

app = FastAPI()
pools_data = Pools()


@app.get("/pools")
async def pools(
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    order_by: str | None = None,
    order: str | None = None,
):
    return {
        "pools": pools_data.entities(skip, limit, search, order_by, order),
    }


@app.get("/pools_count")
async def pools(search: str = None):
    return {
        "total": pools_data.length(search),
    }
