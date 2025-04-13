import itertools
from typing import Dict, List, Self, Callable


class JobGroup:
    def __init__(self):
        self.jobs: Dict[str, BaseJob] = {}

class BaseJob:
    def __init__(self, name: str):
        self.name = name
        self.depends_on = []
        self.steps = []

    def step(self, step: Callable):
        self.steps.append(step)

    def depends(self, *dependencies: List[Self | JobGroup]):
        self.depends_on = list(itertools.chain(*[dependency.jobs.values() if isinstance(dependency, JobGroup) else [dependency] for dependency in dependencies]))

    def run(self, context: Dict):
        for step in self.steps:
            if step(context) == False:
                return False
        
        return True

class Job(BaseJob):
    pass