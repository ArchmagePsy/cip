from cip import stages, jobs

def test_stage_attribute():
    dummy_stage = stages.Stage("dummy")

    assert isinstance(dummy_stage.dummy_job, jobs.Job)
    assert isinstance(dummy_stage.name, str)
    assert "dummy" == dummy_stage.name