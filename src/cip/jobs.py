from typing import Dict, List, Self


class BaseJob:
    def __init__(self, name: str):
        self.name = name
        self.depends_on = []

    def depends(self, dependencies: List[Self]):
        self.depends_on = dependencies

    def run(self, context: Dict):
        pass


class Job(BaseJob):
    pass