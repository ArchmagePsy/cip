"""
This module defines the main entrypoint for any CI?CD process in cip - the pipeline. A pipeline is a collection of stages, groupings of jobs which are
complex units of work that need to be performed as part of integration or deployment. The pipeline ensures that these jobs are all run in order based 
on their dependencies and tracks their status.
"""
import asyncio
import graphlib
import itertools
from typing import Dict

from cip_core.stages import Stage


class BasePipeline:
    """
    This class represents the simplest type of pipeline a cip project can use. It runs jobs one at a time in sequence
    according to when they were defined and which jobs they are dependent on.
    """
    def __init__(self):
        self.stages = {}

    def __getattr__(self, name: str):
        """
        We override the magic method for getting attributes to provide an interface for creating stages in a clean way.

        Usage:
            @my_pipeline.new_stage # defines a new stage called "my_stage" for the pipeline
            my_pipeline.new_stage  # returns the previously defined stage

        Args:
            name(str): the name for the new stage to be added to the pipeline's stages or the existing one to return

        Returns:
            Stage: the newly created or returned stage.
        """
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
        """
        This method starts the pipeline execution. A dependency graph is formed from the jobs and they are sorted topologically
        after which they are iterated through and executed with their own run methods one by one updating the context wherever 
        relevant.

        Args:
            context(Dict): a doctionary containing useful metadata about the pipeline's execution status, it does not need to ordinarily 
                be supplied as the default empty dictionary will be populated accordingly though if any additional metadata needs to be
                added it can be done here.

        Returns:
            Dict[BaseJob, bool]: the results of the different jobs in the pipeline, particularly whether or not they failed.
        """
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
    """
    This is an alias for BasePipeline.
    """
    pass

class AsyncPipeline(BasePipeline):
    """
    This class is an asynchronous version of the pipeline that executes jobs on separate threads so that multiple jobs can be executed
    in parrallel potentially speeding up the runtime of the pipeline. Job dependencies are still maintained such that the workers will
    be blocked whilst no jobs with completed dependencies are available.
    """
    async def run(self, context: Dict = {}, workers: int = 2):
        """
        The execution method for the asynchronous pipeline. Jobs are executed asynchronously whilst maintaining the dependency contraints.
        Contexts are isolated per job so that no unpredicted behaviour should occur where two jobs race to modify a piece of metadata.

        Args:
            context(Dict): a doctionary containing useful metadata about the pipeline's execution status, it does not need to ordinarily 
                be supplied as the default empty dictionary will be populated accordingly though if any additional metadata needs to be
                added it can be done here. Copies of the context will be created each time a job runs to avoid race conditions and other
                unexpected behviour.

            workers(int): the number of asynchronous workers for this pipeline to use.

        Returns:
            Dict[BaseJob, bool]: the results of the different jobs in the pipeline, particularly whether or not they failed.
        """
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