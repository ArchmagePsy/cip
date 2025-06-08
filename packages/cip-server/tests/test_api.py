from itertools import cycle
from cip_server.models.base import Base
from cip_server.models.pipelines import PipelineExecution, PipelineStatus
from cip_server.models.results import JobResult
from cip_server.utils.database import get_session
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from cip_server.api import app
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


postgres = PostgresContainer(username="test_user", password="pass1234", dbname="pipeline_database")

@pytest.fixture(scope="module", autouse=True)
def pipeline_database(request):

    postgres.start()

    def cleanup():
        postgres.stop()

    request.addfinalizer(cleanup)

@pytest_asyncio.fixture
async def pipeline_database_async_engine(pipeline_database):

    engine = create_async_engine(postgres.get_connection_url(driver="asyncpg"))

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()

@pytest_asyncio.fixture
async def pipeline_database_async_session_factory(pipeline_database_async_engine):
    session_factory = sessionmaker(pipeline_database_async_engine, class_=AsyncSession)

    return session_factory

@pytest_asyncio.fixture(autouse=True)
async def setup_database(pipeline_database_async_session_factory: sessionmaker[AsyncSession]):
    async with pipeline_database_async_session_factory() as session:
        pipelines = [PipelineExecution(status=PipelineStatus.FINISHED, git_url=f"/some/repository/{i}/.git", commit_hash="cf4d393fdc5a81bf56ae4895d231865c097007b1") for i in range(5)]
        results = [JobResult(name=f"test_job_{i}", result=(i % 3 == 0)) for i in range(15)]

        for pipeline, result in zip(cycle(pipelines[:3]), results):
            pipeline.job_results.append(result)

        session.add_all(pipelines)
        session.add_all(results)
        
        await session.commit()

@pytest_asyncio.fixture
async def override_dependencies(pipeline_database_async_session_factory):
    async def get_test_session():
        async with pipeline_database_async_session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    yield
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def async_client(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

@pytest.mark.asyncio
async def test_get_all_pipelines(async_client: AsyncClient):
    first_page = await async_client.get("/pipeline", params={"limit": 3})
    assert len(first_page_json := first_page.json()) == 3
    second_page = await async_client.get("/pipeline", params={"limit": 3, "offset": 3})
    assert len(second_page_json := second_page.json()) == 2

@pytest.mark.asyncio
async def test_get_all_results(async_client: AsyncClient):
    pipelines = await async_client.get("/pipeline", params={"limit": 1})
    pipeline_id = pipelines.json()[0]["id"]

    first_page = await async_client.get(f"/pipeline/{pipeline_id}/result", params={"limit": 3})
    assert len(first_page_json := first_page.json()) == 3
    second_page = await async_client.get(f"/pipeline/{pipeline_id}/result", params={"limit": 3, "offset": 3})
    assert len(second_page_json := second_page.json()) == 2
