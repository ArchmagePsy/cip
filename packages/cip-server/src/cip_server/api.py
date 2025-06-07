from fastapi import FastAPI

from cip_server.routes.pipelines import pipeline_router


app = FastAPI()
app.include_router(pipeline_router)