#!/usr/bin/env python3

import os

import github

from github.Repository import Repository
from tenacity import retry, wait_fixed, stop_after_delay


@retry(wait=wait_fixed(30), stop=stop_after_delay(900))
def get_workflow_run_id(repo: Repository, workflow_name: str, branch_name: str) -> int:
    """
    Get the ID of the most recent workflow run.

    :param repo: Repo to get workflow run
    :param workflow_name: Name of the workflow to get run
    :param branch_name: Name of the branch to get run
    :return: ID of the most recent workflow run
    """
    workflow = repo.get_workflow(workflow_name)
    branch = repo.get_branch(branch_name)
    workflow_runs = workflow.get_runs(branch=branch).get_page(0)
    return workflow_runs[0].id


@retry(wait=wait_fixed(30), stop=stop_after_delay(900))
def get_workflow_check_run_status(repo: Repository, check_run_id: int) -> str:
    """
    Get the status of a workflow check run.

    :param repo: Repo to get check run status
    :param check_run_id: ID of the check run to get status
    :return: Status of the check run
    """
    check_run = repo.get_check_run(check_run_id)
    if check_run.status != "completed":
        raise Exception("Check run is still in progress")
    return check_run.conclusion


def main():
    gh_token = os.environ.get("GH_TOKEN")
    gh_branch = os.environ.get("GH_BRANCH", "main")
    gh_workflow_id = os.environ.get("GH_WORKFLOW_ID")
    gh_repo = os.environ.get("GITHUB_REPOSITORY")
    gh = github.Github(gh_token)

    repo = gh.get_repo(gh_repo)
    status = get_workflow_check_run_status(repo, get_workflow_run_id(repo, gh_workflow_id, gh_branch))
    print(f"Workflow status: {status}")


main()
