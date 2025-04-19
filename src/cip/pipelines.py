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
        job_execution_order = job_sorter.static_order()

        results = {}
        context.update(PIPELINE=self)

        def run_job(job):
            context.update(JOB=job, RESULTS=results)
            return job.run(context)

        for job in job_execution_order:
            results[job] = run_job(job)

        return results
    
    def __repr__(self):
        return f"Pipeline({", ".join(self.stages.keys())})"
    
class Pipeline(BasePipeline):
    pass