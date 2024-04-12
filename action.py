#!/usr/bin/env python3

import os

import github
from github.Repository import Repository
from retry import retry


@retry(delay=30, tries=30)
def get_workflow_run_wait(repo: Repository, workflow_name: str, branch_name: str):
    workflow = repo.get_workflow(workflow_name)
    branch = repo.get_branch(branch_name)
    workflow_runs = workflow.get_runs(branch=branch).get_page(0)
    for workflow_run in workflow_runs:
        if workflow_run.status not in ['in_progress', 'queued', 'requested', 'pending', 'waiting']:
            return workflow_run.status


def main():
    gh_token = os.environ.get("GH_TOKEN")
    gh_owner = os.environ.get("GH_OWNER")
    gh_repo = os.environ.get("GH_REPO")
    gh_branch = os.environ.get("GH_BRANCH", "main")
    gh_workflow_id = os.environ.get("GH_WORKFLOW_ID")
    gh = github.Github(gh_token)

    repo = gh.get_repo(f"{gh_owner}/{gh_repo}")
    status = get_workflow_run_wait(repo, gh_workflow_id, gh_branch)
    if status == "completed":
        print(f"::set-output name=status::{status}")
    else:
        print(f"::error::Workflow run status is {status}")


main()
