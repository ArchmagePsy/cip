import graphlib
from typing import Dict

from cip.jobs import Job


class BasePipeline:
    def __init__(self):
        self.jobs = {}

    def __getattr__(self, name: str):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            if name not in self.jobs:
                new_job = Job(name)
                self.jobs[name] = new_job
                return new_job
            else:
                return self.jobs[name]
            
    def run(self, context: Dict = {}):
        dependency_graph = {job: job.depends_on for job in self.jobs.values()}

        job_sorter = graphlib.TopologicalSorter(dependency_graph)
        job_execution_order = job_sorter.static_order()

        context.update(PIPELINE=self)

        def run_job(job):
            context.update(JOB=job)
            return job.run(context)

        results = {job: run_job(job) for job in job_execution_order}

        return results
    
class Pipeline(BasePipeline):
    pass