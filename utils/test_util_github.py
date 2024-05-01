"""Provides test for GitHub utility."""
from pathlib import Path
from unittest.mock import MagicMock
import mock
import os


from action import get_github_access_token, get_workflow_run_id, get_github_jwt, get_workflow_status


def test_get_github_jwt() -> None:
    """
    When the GitHub JWT is created, the JWT token should be returned.

    :return:
    """
    app_id = 'app_id'
    os.system('openssl genrsa -out private-key.pem 2048')
    pem = 'private-key.pem'
    jwt_token = get_github_jwt(app_id, pem)
    assert jwt_token is not None
    pem_file_path = Path(pem)
    pem_file_path.unlink()


def test_get_github_access_token() -> None:
    """
    When the GitHub App access token is requested, the token should be returned.

    :return:
    """
    app_id = 'app_id'
    installation_id = 'installation_id'
    os.system('openssl genrsa -out private-key.pem 2048')
    pem = 'private-key.pem'
    with mock.patch('action.get_github_jwt') as mock_get_github_jwt:
        mock_get_github_jwt.return_value = 'jwt_token'
        with mock.patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = {'token': 'access_token'}
            access_token = get_github_access_token(app_id, installation_id, pem)
            assert access_token == 'access_token'
    pem_file_path = Path(pem)
    pem_file_path.unlink()


def test_get_workflow_run_id_should_return_id() -> None:
    """
    The ID of the most recent workflow run should be returned.

    :return:
    """
    workflow_run = MagicMock()
    workflow_run.id = 123

    workflow = MagicMock()
    workflow.get_runs.return_value.get_page.return_value = [workflow_run]

    repo = MagicMock()
    repo.get_workflow = MagicMock(return_value=workflow)
    repo.get_branch = MagicMock(return_value='main')

    assert get_workflow_run_id(repo, 'check-workflow', 'main') == 123


def test_get_workflow_status_should_return_conclusion() -> None:
    """
    The conclusion of the workflow should be returned.

    :return:
    """
    workflow_run = MagicMock()
    workflow_run.status = 'completed'
    workflow_run.conclusion = 'success'

    repo = MagicMock()
    repo.get_workflow_run = MagicMock(return_value=workflow_run)

    assert get_workflow_status(repo, 123) == 'success'
