from cip_server.config import get_config
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_config().database.url(async_db=True))
    else:
        return _engine

def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(get_engine(), class_=AsyncSession)
    else:
        return _session_factory

async def get_session():
    async with get_session_factory() as session:
        yield session