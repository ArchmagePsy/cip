import itertools
from typing import Dict, List, Self, Callable


class JobGroup:
    def __init__(self):
        self.jobs: Dict[str, BaseJob] = {}

class BaseJob:
    def __init__(self, name: str, allowed_to_fail: bool = False):
        self.name = name
        self.allowed_to_fail = allowed_to_fail
        self.depends_on = []
        self.steps = []

    def step(self, step: Callable):

        def step_wrapper(context: Dict):
            return True if (result := step(context)) is None else result

        self.steps.append(step_wrapper)

    def depends(self, *dependencies: List[Self | JobGroup]):
        self.depends_on = list(itertools.chain(*[dependency.jobs.values() if isinstance(dependency, JobGroup) else [dependency] for dependency in dependencies]))

    def allow_fail(self, allow: bool = True):
        self.allowed_to_fail = allow

    def run(self, context: Dict):
        if not all([context["RESULTS"][dependency] for dependency in self.depends_on]):
            return None

        for step in self.steps:
            if not step(context) and not self.allowed_to_fail:
                return False
        
        return True

class Job(BaseJob):
    pass