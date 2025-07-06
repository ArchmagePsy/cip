
from cip_client.config import get_config
from cip_client.errors import CipClientException
from pathlib import Path
import requests
import enum
import os


commit = merge = """
#!/bin/bash

cip-client run {repository} $(git rev-parse HEAD)
"""

push = """
#!/bin/bash

while read oldrev newrev refname; do
    if [[ "$refname" != refs/heads/* ]]; then
        continue
    fi

    if [[ "$newrev" == "0000000000000000000000000000000000000000" ]]; then
        continue
    fi

    cip-client run {repository} "$newrev"
done
"""

hook_scripts = [commit, merge, push]

class CipStrategy(enum.Enum):
    COMMIT  = 0
    MERGE   = 1
    PUSH    = 2

class CipClientCli:

    def __init__(self):
        self.config = get_config()

    def install(self, repo_path: os.PathLike = os.path.join(os.getcwd(), ".git"), strategy: CipStrategy = CipStrategy.COMMIT):
        if not os.path.exists(repo_path):
            raise CipClientException(f"Path {repo_path} is not a git repository")
        
        repo_url = f"{self.config.git_server_url}/repository/{repo_path.split(os.sep)[-2]}.git"
        
        hooks_path = os.path.join(repo_path, "hooks")
        
        hook_file_path = os.path.join(hooks_path, ["post-commit", "post-merge", "post-receive"][strategy.value])
        Path(hook_file_path).write_text(hook_scripts[strategy.value].format(repository=repo_url))
        os.chmod(hook_file_path, mode=0o755)

    def run(self, repository: str, commit_hash: str):
        response = requests.post(f"{self.config.api_url}/pipeline", params={
            "git_url": repository,
            "commit_hash": commit_hash
        })

        return response.content.decode()