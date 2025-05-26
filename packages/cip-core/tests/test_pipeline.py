from typing import Dict
from cip_core import pipelines, stages


def test_pipeline_attribute():
    dummy_pipeline = pipelines.Pipeline()

    assert isinstance(dummy_pipeline.stages, dict)
    assert isinstance(dummy_pipeline.dummy_stage, stages.Stage)
    assert "dummy_stage" in dummy_pipeline.stages.keys()

def test_pipeline_repr():
    dummy_pipeline = pipelines.Pipeline()
    dummy_pipeline.dummy_stage
    dummy_pipeline.dummy_stage1

    assert repr(dummy_pipeline) == "Pipeline(dummy_stage, dummy_stage1)"

def test_pipeline_run():
    dummy_pipeline = pipelines.Pipeline()

    @dummy_pipeline.stage2.job1.step
    def step4(context: Dict):
        assert context["RESULTS"][dummy_pipeline.stage1.job1] and context["RESULTS"][dummy_pipeline.stage1.job2]

    @dummy_pipeline.stage1.job1.step
    def step1(context: Dict):
        assert context["PIPELINE"] == dummy_pipeline
        assert context["JOB"] == dummy_pipeline.stage1.job1
        assert context["STEP"] == "step1"
        assert "RESULTS" in context
        return False

    @dummy_pipeline.stage1.job1.step
    def step2(context: Dict):
        assert False

    dummy_pipeline.stage1.job1.allow_fail()

    @dummy_pipeline.stage1.job2.step
    def step3(context: Dict):
        assert context["RESULTS"][dummy_pipeline.stage1.job1]

    dummy_pipeline.stage2.job1.depends(dummy_pipeline.stage1)

    dummy_pipeline.run()

def test_pipeline_run_concurrent():
    dummy_pipeline = pipelines.ConcurrentPipeline()

    @dummy_pipeline.stage2.job1.step
    def step4(context: Dict):
        assert context["RESULTS"][dummy_pipeline.stage1.job1] and context["RESULTS"][dummy_pipeline.stage1.job2]

    @dummy_pipeline.stage1.job1.step
    def step1(context: Dict):
        assert context["PIPELINE"] == dummy_pipeline
        assert context["JOB"] == dummy_pipeline.stage1.job1
        assert context["STEP"] == "step1"
        assert "RESULTS" in context
        return False

    @dummy_pipeline.stage1.job1.step
    def step2(context: Dict):
        assert False

    dummy_pipeline.stage1.job1.allow_fail()

    @dummy_pipeline.stage1.job2.step
    def step3(context: Dict):
        assert context["RESULTS"][dummy_pipeline.stage1.job1]

    dummy_pipeline.stage2.job1.depends(dummy_pipeline.stage1)
    # this prevents race condition between job1 and job2 in stage1
    dummy_pipeline.stage1.job2.depends(dummy_pipeline.stage1.job1)

    dummy_pipeline.run()