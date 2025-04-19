import asyncio
import graphlib
import itertools
from typing import Dict

from cip.stages import Stage


class BasePipeline:
    def __init__(self):
        self.stages = {}

    def __getattr__(self, name: str):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            if name not in self.stages:
                new_stage = Stage(name)
                self.stages[name] = new_stage
                return new_stage
            else:
                return self.stages[name]
            
    def run(self, context: Dict = {}):
        dependency_graph = {job: job.depends_on for job in itertools.chain(*[stage.jobs.values() for stage in self.stages.values()])}

        job_sorter = graphlib.TopologicalSorter(dependency_graph)

        results = {}
        context.update(PIPELINE=self)

        def run_job(job):
            context.update(JOB=job, RESULTS=results)
            return job.run(context)

        job_sorter.prepare()

        while job_sorter.is_active():
            jobs = job_sorter.get_ready()
            for job in jobs:
                results[job] = run_job(job)
                job_sorter.done(job)

        return results
    
    def __repr__(self):
        return f"Pipeline({", ".join(self.stages.keys())})"
    
class Pipeline(BasePipeline):
    pass

class AsyncPipeline(BasePipeline):
    async def run(self, context: Dict = {}, workers: int = 2):
        dependency_graph = {job: job.depends_on for job in itertools.chain(*[stage.jobs.values() for stage in self.stages.values()])}

        job_sorter = graphlib.TopologicalSorter(dependency_graph)
        job_queue = asyncio.Queue()

        results = {}
        context.update(PIPELINE=self)

        def run_job(job):
            local_context = context.copy()
            local_context.update(JOB=job, RESULTS=results)
            return job.run(local_context)
        
        def populate_queue():
            for job in job_sorter.get_ready():
                job_queue.put_nowait(job)
        
        async def run_jobs():
            while job_sorter.is_active():
                try:
                    job = job_queue.get_nowait()
                    results[job] = await asyncio.to_thread(run_job, job)
                    job_sorter.done(job)
                    job_queue.task_done()
                    populate_queue()
                except asyncio.QueueEmpty:
                    await asyncio.sleep(0)

        job_sorter.prepare()

        populate_queue()
        await asyncio.gather(*[asyncio.create_task(run_jobs()) for _ in range(workers)])

        return results