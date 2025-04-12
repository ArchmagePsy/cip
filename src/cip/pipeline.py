from cip.jobs import Job


class BasePipeline:
    def __init__(self):
        self.jobs = {}

    def __getattr__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            if name not in self.jobs:
                new_job = Job()
                self.jobs[name] = new_job
                return new_job
            else:
                return self.jobs[name]