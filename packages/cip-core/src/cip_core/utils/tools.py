"""
This module contains decorators that can be added to functions in order to expose tools to your methods. A tool is essentially a dependency that you
inject into your jobs which allows you to call some external process or module. The most common use case of tools is providing chell access to your jobs
in order to run external build systems, testing solutions, etc.
"""
import functools
import inspect
from os import PathLike
import os
import subprocess
import tempfile
from typing import Callable, Dict, List


def process(fail_fast: bool = True, shell: bool = False, executable: PathLike | None = None):
    """
    This tool wraps a job step and passes a process dependency as the first argument.
    Calling the dependency executes the given command in a separate subprocess.

    Args:
        fail_fast(bool): determines whether or not the job step should fail as soon as a call to process
            fails with a nonzero returncode (breaking the step's execution) or instead keep executing until
            the step is finished and return a failure only then. (this defaults to True)

        shell(bool): determines whether or not to execute the subprocesses in a shell context. (This defaults to False)
        
        executable(PathLike): the executable to pass commands to, defaults to whatever the default system shell
            interpreter is.

    Returns:
        Callable: the decorator used to wrap the step definition.
    """
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
                environment.update(**dict(map(lambda item: (item[0], str(item[1])), context.items())))
                step_result = step(process_patch, context)
                return result and (step_result or step_result is None)
            except subprocess.CalledProcessError:
                return False
            
        return process_wrapper
    
    return process_decorator

def process_default(step: Callable):
    """
    This is the default configuration of the process decorator.
    """
    return process()(step)

def shell(fail_fast: bool = True, executable: PathLike | None = None):
    """
    This tool wraps the job step with a shell allowing it to execute more complex commands. It functions
    as a reconfiguration of the process tool decorator.

    Args:
        fail_fast(bool): determines whether or not the job step should fail as soon as a call to process
            fails with a nonzero returncode (breaking the step's execution) or instead keep executing until
            the step is finished and return a failure only then. (this defaults to True)

        executable(PathLike): the executable to pass commands to, defaults to whatever the default system shell
            interpreter is.

    Returns:
        Callable: the decorator used to wrap the step definition.
    """
    return process(fail_fast=fail_fast, shell=True, executable=executable)

def shell_default(step: Callable):
    """
    This is the default configuration of the shell decorator.
    """
    return process(shell=True)(step)

def script(interpreter: PathLike):
    """
    This tool wraps a job step and extracts the docstring attached to it writing it out to a temporary file
    and setting it as executable. The tool then executes this script using the given interpreter. This way you
    can (almost) seemlessly integrate in-place scripts using external interpreters.

    Args:
        interpreter(PathLike): the path to the interpreter used to execute the script.

    Returns:
        Callable: the decorator used to wrap the step definition.
    """
    def script_decorator(step: Callable):
        script_text = inspect.getdoc(step)
        script_text = f"#!{interpreter}\n\n" + script_text
        environment = os.environ.copy()

        @functools.wraps(step)
        def script_wrapper(context: Dict):
            environment.update(**dict(map(lambda item: (item[0], str(item[1])), context.items())))
            script_temp = tempfile.NamedTemporaryFile()
            script_temp.write(script_text.encode())
            script_temp.seek(0)
            os.chmod(script_temp.name, 0o1700)
            completed_process: subprocess.CompletedProcess = subprocess.run(f"{script_temp.name}", shell=True, executable=interpreter, env=environment)
            return completed_process.returncode == 0
        
        return script_wrapper
    
    return script_decorator

def bash(step: Callable):
    """
    This is a configuration of the script tool that executes scripts using the Bourne Again SHell (BASH) interpreter.
    """
    return script("/bin/bash")(step)

def sh(step: Callable):
    """
    This is a configuration of the script tool that executes scripts using the system's default shell through 'sh'.
    """
    return script("/bin/sh")(step)