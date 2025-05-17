"""
This module defines the basic building blocks of pipelines, jobs. Jobs are executed according to their dependencies when
a pipeline is run and each one can contain one or more steps.
"""
import functools
import itertools
from typing import Dict, List, Self, Callable


class JobGroup:
    """
    This class defines a bsic interface for interacting with a collection of jobs.
    """
    def __init__(self):
        self.jobs: Dict[str, BaseJob] = {}

    def allow_fail(self, allowed: bool = True):
        """
        Set the flag for all jobs in this group to allow failure of a job.
        
        Args:
            allowed(bool): whether or not jobs in this group are allowed to fail.
        """
        for job in self.jobs.values():
            job.allow_fail(allowed)

class BaseJob:
    """
    The base job implementation. This class defines all the simple methods and essential
    attributes a job requires.
    """
    def __init__(self, name: str, allowed_to_fail: bool = False):
        """
        Args:
            name(str): the name to be given to the job.

            allowed_to_fail(bool): whether or not this job is allowed to fail.
        """
        self.name = name
        self.allowed_to_fail = allowed_to_fail
        self.depends_on = []
        self.steps = []

    def step(self, step: Callable):
        """
        A job is made up of multiple steps, each one is executed in the order they are defined.
        This method is used to decorate a function definition and wrap it as the instructions 
        that are executed as part of that step.

        Args:
            step(Callable): the function definition to be added to this job as a step. This function will
                be wrapped so that it returns True unless it would return False. In order to ensure that
                a Job can always definitively concluded in a success or a failure.
        """
        @functools.wraps(step)
        def step_wrapper(context: Dict):
            return True if (result := step(context)) is None else result

        self.steps.append(step_wrapper)

    def depends(self, *dependencies: List[Self | JobGroup]):
        """
        Set the jobs that this job depends on. If a Job depends on another then it will only run when the jobs
        it depends on have finished executing. Note that this method will overwrite any previously defined
        dependencies for this job.

        Args:
            dependencies(List[BaseJob | JobGroup]): the jobs or job groups this job is dependent on.
        """
        self.depends_on = list(itertools.chain(*[dependency.jobs.values() if isinstance(dependency, JobGroup) else [dependency] for dependency in dependencies]))

    def allow_fail(self, allowed: bool = True):
        """
        Set whether this job is allowed to fail or not. A job that is allowed to fail will always return True (will always succeed).

        Args:
            allowed(bool): whether or not this job is allowed to fail.
        """
        self.allowed_to_fail = allowed

    def run(self, context: Dict):
        """
        This method executes the job and returns its result.

        Args:
            context(Dict): the context contains useful metadata about the pipeline execution that is passed through the steps
                of the job. This is supplied and ideally managed by the pipeline itself.
        """
        if not all([context["RESULTS"].get(dependency, False) for dependency in self.depends_on]):
            return None

        for step in self.steps:
            context.update(STEP=step.__name__)
            if not step(context):
                return self.allowed_to_fail
        
        return True
    
    def __repr__(self):
        return f"Job(name: {self.name}, steps: [{", ".join(list(map(lambda step: step.__name__, self.steps)))}])"

class Job(BaseJob):
    """
    This is just an alias for BaseJob.
    """
    pass