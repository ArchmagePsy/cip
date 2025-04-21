from cip import pipelines, stages


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

