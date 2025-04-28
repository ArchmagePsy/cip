import functools
import itertools
from typing import Dict, List, Self, Callable


class JobGroup:
    def __init__(self):
        self.jobs: Dict[str, BaseJob] = {}

    def allow_fail(self, allowed: bool = True):
        for job in self.jobs.values():
            job.allow_fail(allowed)

class BaseJob:
    def __init__(self, name: str, allowed_to_fail: bool = False):
        self.name = name
        self.allowed_to_fail = allowed_to_fail
        self.depends_on = []
        self.steps = []

    def step(self, step: Callable):

        @functools.wraps(step)
        def step_wrapper(context: Dict):
            return True if (result := step(context)) is None else result

        self.steps.append(step_wrapper)

    def depends(self, *dependencies: List[Self | JobGroup]):
        self.depends_on = list(itertools.chain(*[dependency.jobs.values() if isinstance(dependency, JobGroup) else [dependency] for dependency in dependencies]))

    def allow_fail(self, allowed: bool = True):
        self.allowed_to_fail = allowed

    def run(self, context: Dict):
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
    pass