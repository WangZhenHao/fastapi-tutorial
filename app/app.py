from fastapi import FastAPI
from app.db import create_db_and_tables, get_async_session, Post
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

test = FastAPI(lifespan=lifespan)


@test.get('/')
def root():
    return {"message": "Hello World"}