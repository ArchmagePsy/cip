import asyncio
import time
from typing import Dict

from cip import pipelines
from cip.utils import tools

my_pipeline = pipelines.AsyncPipeline()

@my_pipeline.deploy.push_job_2.step
def failing_job(context: Dict):
    print("step failed")
    return False

my_pipeline.deploy.push_job_2.allow_fail()

@my_pipeline.deploy.push_job.step
def third_step(context: Dict):
    print("you will only see this after build has finished")

@my_pipeline.build.demo_job.step
def demo_step(context: Dict):
    print("this is a demo of the cip DSL!")

@my_pipeline.build.demo_job.step
def second_step(context: Dict):
    print(f"This is part of the '{context["JOB"].name}' job!")

@my_pipeline.build.demo_job.step
@tools.process_default
def step_with_cmd(cmd, context: Dict):
    cmd("pwd")

@my_pipeline.build.demo_job.step
@tools.shell_default
def step_with_shell(shell, context: Dict):
    shell("echo \"live from a shell\"")
    shell('echo "$PIPELINE $JOB $STEP $RESULTS"')

@my_pipeline.build.demo_job.step
@tools.sh
def step_with_bash_script():
    """
    for i in $(seq 1 10);
    do
        echo $i;
    done
    """

my_pipeline.deploy.push_job.depends(my_pipeline.build)

@my_pipeline.unreachable.invisible_job.step
def invisible(context: Dict):
    print("you'll never see me")

my_pipeline.unreachable.invisible_job.depends(my_pipeline.deploy.push_job_2)

if __name__ == "__main__":
    t0 = time.time()
    print(asyncio.run(my_pipeline.run()))
    #my_pipeline.run()
    t1 = time.time()

    print(t1-t0)