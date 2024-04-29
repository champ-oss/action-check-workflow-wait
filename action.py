import time
import logging

import github.Auth
import jwt
import requests
import os

from github import Repository
from tenacity import retry, wait_fixed, stop_after_attempt, stop_after_delay

logging.basicConfig(
    format='%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def create_github_jwt(app_id: str, pem: str) -> str:
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
    with open(pem, 'r') as file:
        private_key = file.read()
    jwt_token = jwt.encode(payload, private_key, algorithm='RS256')
    return jwt_token


def get_github_access_token(app_id: str, installation_id: str, pem: str) -> str:
    """
    Get GitHub App access token.

    :param app_id: GitHub App's identifier
    :param installation_id: GitHub App's installation identifier
    :param pem: Path to the private
    :return: GitHub App access token
    """
    create_jwt = create_github_jwt(app_id, pem)
    response = requests.post(
        f'https://api.github.com/app/installations/{installation_id}/access_tokens',
        headers={
            'Authorization': f'Bearer {create_jwt}',
            'Accept': 'application/vnd.github+json'
        }
    )
    response.raise_for_status()
    access_token = response.json()['token']
    return access_token


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
    workflow_runs = workflow.get_runs(branch=branch).get_page(0)
    return workflow_runs[0].id


@retry(wait=wait_fixed(15), stop=(stop_after_delay(900)))
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
    else:
        raise Exception('Workflow is still running')


def main():
    app_id = os.environ.get('GH_APP_ID')
    installation_id = os.environ.get('GH_INSTALLATION_ID')
    private_key = os.environ.get('GH_APP_PRIVATE_KEY')
    gh_owner_repo = os.environ.get('GITHUB_REPOSITORY')
    get_workflow_name = os.environ.get('GH_WORKFLOW_NAME')
    updated_private_key = private_key.replace('\\n', '\n').strip('"')
    # write private key to file
    with open('private.pem', 'w') as file:
        file.write(updated_private_key)
    # Get access token
    access_token = get_github_access_token(app_id, installation_id, 'private.pem')
    github_client = github.Github(access_token)
    repo = github_client.get_repo(gh_owner_repo)
    workflow_run_id = get_workflow_run_id(repo, get_workflow_name, 'main')
    logger.info(f'Workflow run id: {workflow_run_id}')
    workflow_check_runs_status = get_workflow_status(repo, workflow_run_id)
    if workflow_check_runs_status == 'success':
        logger.info('Workflow run successfully')
    else:
        logger.error('Workflow run failed')
        raise Exception('Workflow run failed')


if __name__ == '__main__':
    main()
