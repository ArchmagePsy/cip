import functools
import inspect
from os import PathLike
import os
import subprocess
import tempfile
from typing import Callable, Dict, List


def process(fail_fast: bool = True, shell: bool = False, executable: PathLike | None = None):
    def process_decorator(step: Callable):
        result = True
        environment = os.environ.copy()

        def process_patch(cmd: str, *args: List[str]):
            nonlocal result
            completed_process: subprocess.CompletedProcess =  subprocess.run([cmd, *args], shell=shell, executable=executable, env=environment)
            if fail_fast:
                completed_process.check_returncode()
            else:
                result = result and (completed_process.returncode == 0)

            return completed_process

        @functools.wraps(step)
        def process_wrapper(context: Dict):
            nonlocal environment
            try:
                environment.update(**dict(map(lambda item: (item[0], repr(item[1])), context.items())))
                return result and step(process_patch, context)
            except subprocess.CalledProcessError:
                return False
            
        return process_wrapper
    
    return process_decorator

def process_default(step: Callable):
    return process()(step)

def shell(fail_fast: bool = True, executable: PathLike | None = None):
    return process(fail_fast=fail_fast, shell=True, executable=executable)

def shell_default(step: Callable):
    return process(shell=True)(step)

def script(interpreter: PathLike):
    def script_decorator(step: Callable):
        script_text = inspect.getdoc(step)
        script_text = f"#!{interpreter}\n\n" + script_text
        environment = os.environ.copy()

        @functools.wraps(step)
        def script_wrapper(context: Dict):
            environment.update(**dict(map(lambda item: (item[0], repr(item[1])), context.items())))
            script_temp = tempfile.NamedTemporaryFile()
            script_temp.write(script_text.encode())
            script_temp.seek(0)
            os.chmod(script_temp.name, 0o1700)
            completed_process: subprocess.CompletedProcess = subprocess.run(f"{script_temp.name}", shell=True, executable=interpreter, env=environment)
            return completed_process.returncode == 0
        
        return script_wrapper
    
    return script_decorator

def bash(step: Callable):
    return script("/bin/bash")(step)

def sh(step: Callable):
    return script("/bin/sh")(step)