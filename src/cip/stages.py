from cip.jobs import Job, JobGroup


class Stage(JobGroup):
    def __init__(self, name):
        self.name = name
        super().__init__()

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