from typing import Dict, List, Self, Callable


class BaseJob:
    def __init__(self, name: str):
        self.name = name
        self.depends_on = []
        self.stages = []

    def stage(self, stage: Callable):
        self.stages.append(stage)

    def depends(self, dependencies: List[Self]):
        self.depends_on = dependencies

    def run(self, context: Dict):
        for stage in self.stages:
            if stage(context) == False:
                return False
        
        return True


class Job(BaseJob):
    pass