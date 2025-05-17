"""
This module defines the stage, a pipeline's method for grouping jobs that form a particular phase of the CI/CD lifecycle.
"""
from cip_core.jobs import Job, JobGroup


class Stage(JobGroup):
    """
    This class defines a Stage in the pipeline. A stage is a group of jobs all dedicated to one purpose normally building, testing, or deploying.
    """
    def __init__(self, name):
        """
        Args:
            name(str): the name for this stage.
        """
        self.name = name
        super().__init__()

    def __getattr__(self, name: str):
        """
        We override the magic method for getting object attributes to provide an interface for cleanly defining new jobs in a stage.

        Usage:
            @my_stage.new_job # declares a job called "new_job" and adds it to the my_stage job group.
            my_stage.new_job  # returns the previously created job

        Args:
            name(str): the name for the new job.

        Returns:
            BaseJob: the job under the given name belonging to this stage or the newly created job if none exists already.
        """
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            if name not in self.jobs:
                new_job = Job(name)
                self.jobs[name] = new_job
                return new_job
            else:
                return self.jobs[name]