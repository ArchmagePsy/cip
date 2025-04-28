from typing import Dict
from cip_core.utils import tools


# these tests will only work on unix systems

def test_tools_process():

    @tools.process(fail_fast=True)
    def fast_fail(cmd, context: Dict):
        cmd("false")
        assert False

    fast_fail({})

def test_tool_shell():

    @tools.shell()
    def slow_fail_env(cmd, context: Dict):
        cmd("false")
        cmd("echo $CANARY > /tmp/canary.txt")
        
        with open("/tmp/canary.txt") as test_file:
            assert test_file.read() == "yellow-bird\n"

        cmd("rm -f /tmp/canary.txt")
        
    assert slow_fail_env({"CANARY": "yellow-bird"}) == False


def test_tools_script():
    @tools.script("/bin/sh")
    def run_script(context: Dict):
        """
        echo $CANARY > /tmp/canary.txt
        if test "$(cat /tmp/canary.txt)" = "in-the-mine"
        then
            rm -f /tmp/canary.txt
            exit 0
        else
            rm -f /tmp/canary.txt
            exit 1
        fi
        """
        assert False

    assert run_script({"CANARY": "in-the-mine"})