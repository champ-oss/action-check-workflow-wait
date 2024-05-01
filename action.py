"""Provides action for wait on Github workflow based on status."""
import time
import logging

import github.Auth
import jwt
import requests
import os
from github import Repository
from pathlib import Path
from tenacity import retry, wait_fixed, stop_after_delay
import re

logging.basicConfig(
    format='%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_github_jwt(app_id: str, pem: str) -> str:
    """
    Create GitHub JWT.

    :param app_id: GitHub App's identifier
    :param pem: Path to the private
    :return: GitHub JWT
    """
    time_now = int(time.time())
    payload = {
        'iat': time_now,
        'exp': time_now + (10 * 60),
        'iss': app_id
    }
    pem_file_path = Path(pem)
    with pem_file_path.open('r') as file:
        private_key = file.read()
    return jwt.encode(payload, private_key, algorithm='RS256')


def get_github_access_token(app_id: str, installation_id: str, pem: str) -> str:
    """
    Get GitHub App access token.

    :param app_id: GitHub App's identifier
    :param installation_id: GitHub App's installation identifier
    :param pem: Path to the private
    :return: GitHub App access token
    """
    get_jwt = get_github_jwt(app_id, pem)
    response = requests.post(
        f'https://api.github.com/app/installations/{installation_id}/access_tokens',
        headers={
            'Authorization': f'Bearer {get_jwt}',
            'Accept': 'application/vnd.github+json'
        }
    )
    response.raise_for_status()
    return response.json()['token']


def get_workflow_run_id(repo: Repository, workflow_name: str, branch: str) -> int:
    """
    Get the ID of the workflow run.

    :param repo: Repo to get workflow run ID
    :param workflow_name: Name of the workflow
    :param branch: Branch of the workflow
    :return: ID of the workflow run
    """
    workflow = repo.get_workflow(workflow_name)
    branch = repo.get_branch(branch)
    try:
        workflow_runs = workflow.get_runs(branch=branch).get_page(0)
    except Exception:
        logger.exception('Error getting workflow run')
        raise
    return workflow_runs[0].id


@retry(wait=wait_fixed(15), stop=stop_after_delay(900))
def get_workflow_status(repo: Repository, workflow_run_id: int) -> str:
    """
    Get the status of the workflow.

    :param repo: Repo to get workflow status
    :param workflow_run_id: ID of the workflow run
    :return: Status of the workflow
    """
    workflow_run = repo.get_workflow_run(workflow_run_id)
    if workflow_run.status not in ['in_progress', 'queued', 'requested', 'pending', 'waiting']:
        return workflow_run.conclusion

    logger.info(f'Workflow run status: {workflow_run.status}')
    # create own exception for retry
    raise Exception('Workflow run is still in progress')


def main() -> None:
    """
    Handle the main execution of the action workflow.

    :return: None
    """
    app_id = os.environ.get('GH_APP_ID')
    installation_id = os.environ.get('GH_INSTALLATION_ID')
    private_key = os.environ.get('GH_APP_PRIVATE_KEY')
    gh_owner_repo = os.environ.get('GITHUB_REPOSITORY')
    get_workflow_name = os.environ.get('GH_WORKFLOW_NAME')
    updated_private_key = re.sub(r'\\n', '\n', private_key)
    # write private key to file
    private_key_file = Path('private.pem')
    with private_key_file.open('w') as file:
        file.write(updated_private_key)
    access_token = get_github_access_token(app_id, installation_id, 'private.pem')
    github_client = github.Github(access_token)
    repo = github_client.get_repo(gh_owner_repo)
    workflow_run_id = get_workflow_run_id(repo, get_workflow_name, 'main')
    logger.info(f'Workflow run id: {workflow_run_id}')
    workflow_get_status = get_workflow_status(repo, workflow_run_id)
    if workflow_get_status == 'success':
        logger.info('Workflow run successfully')
    else:
        logger.error('Workflow run failed')
        raise Exception('Workflow run failed')


if __name__ == '__main__':
    main()
