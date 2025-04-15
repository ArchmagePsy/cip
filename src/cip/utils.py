import functools
import subprocess
from typing import Callable, Dict, List


def process(fail_fast: bool = True):
    def process_decorator(step: Callable):
        result = True

        def process_patch(cmd: str, *args: List[str]):
            nonlocal result
            completed_process: subprocess.CompletedProcess =  subprocess.run([cmd, *args])
            if fail_fast:
                completed_process.check_returncode()
            else:
                result = result and (completed_process.returncode == 0)

        @functools.wraps(step)
        def process_wrapper(context: Dict):
            try:
                return result and step(process_patch, context)
            except subprocess.CalledProcessError:
                return False
            
        return process_wrapper
    
    return process_decorator

def process_default(step: Callable):
    return process()(step)
