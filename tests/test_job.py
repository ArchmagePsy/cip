from cip import jobs

def test_job_allow_fail():
    dummy_job_1 = jobs.Job("dummy_1")
    dummy_job_2 = jobs.Job("dummy_2", True)

    assert not dummy_job_1.allowed_to_fail
    assert dummy_job_2.allowed_to_fail

    dummy_group = jobs.JobGroup()
    dummy_group.jobs.update(dummy_1=dummy_job_1, dummy_2=dummy_job_2)
    dummy_group.allow_fail()

    assert dummy_job_1.allowed_to_fail
    assert dummy_job_2.allowed_to_fail

def test_job_step():
    dummy_job = jobs.Job("dummy")
    @dummy_job.step
    def step_1(context):
        pass

    assert dummy_job.steps[0].__name__ == "step_1"
    assert dummy_job.steps[0]({})

def test_job_depends():
    dummy_job_1 = jobs.Job("dummy_1")
    dummy_job_2 = jobs.Job("dummy_2")
    dummy_group = jobs.JobGroup()
    dummy_group.jobs.update(dummy_1=dummy_job_1, dummy_2=dummy_job_2)
    
    dummy_job_3 = jobs.Job("dummy_3")
    dummy_job_4 = jobs.Job("dummy_4")

    dummy_job_4.depends(dummy_job_3, dummy_group)

    assert dummy_job_1 in  dummy_job_4.depends_on
    assert dummy_job_2 in  dummy_job_4.depends_on
    assert dummy_job_3 in  dummy_job_4.depends_on

def test_job_repr():
    dummy_job = jobs.Job("dummy")
    @dummy_job.step
    def step_1():
        pass

    @dummy_job.step
    def step_2():
        pass

    assert repr(dummy_job) == "Job(name: dummy, steps: [step_1, step_2])"

def test_job_run():
    dummy_job_1 = jobs.Job("dummy_1")
    dummy_job_2 = jobs.Job("dummy_2")
    dummy_job_3 = jobs.Job("dummy_3")

    dummy_job_3.depends(dummy_job_1, dummy_job_2)

    @dummy_job_3.step
    def always_fails(context):
        assert context["STEP"] == "always_fails"
        return False
    
    assert dummy_job_3.run(dict(RESULTS={dummy_job_1: True})) is None
    assert dummy_job_3.run(dict(RESULTS={dummy_job_1: True, dummy_job_2: True})) == False
    dummy_job_3.allow_fail()
    assert dummy_job_3.run(dict(RESULTS={dummy_job_1: True, dummy_job_2: True})) == True
