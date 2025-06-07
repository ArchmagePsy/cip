from cip_server.config import CipServerConfig
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


config = CipServerConfig()
db_engine = create_async_engine(config.database.url(async_db=True))
session_factory = sessionmaker(db_engine, class_=AsyncSession)

async def get_session():
    async with session_factory() as session:
        yield session