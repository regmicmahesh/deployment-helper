import base64
import os
import structlog
import logging

from deployment_helper.core.clients import github
from deployment_helper.core.llm_engine import generate_iam_policy_from_repository

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)


COHERE_API_KEY = os.environ["COHERE_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

GITHUB_REPOSITORY_NAME = "regmicmahesh/test-pull-request"
GITHUB_BRANCH_NAME = "main"


async def run_with_github_apps_installation(
    *,
    github_repository_name: str,
    github_branch_name: str,
    pull_request_id: int,
):
    github_app_private_key_base64 = os.environ["GITHUB_APP_PRIVATE_KEY"]
    github_app_private_key = base64.b64decode(github_app_private_key_base64)

    github_app_client_id = os.environ["GITHUB_APP_CLIENT_ID"]

    github_access_token = await github.get_github_apps_access_token(
        repository_path=github_repository_name,
        jwt_private_key=github_app_private_key,
        client_id=github_app_client_id,
    )

    iam_policy = await generate_iam_policy_from_repository(
        github_access_token=github_access_token,
        cohere_api_key=COHERE_API_KEY,
        openai_api_key=OPENAI_API_KEY,
        github_repository_name=github_repository_name,
        github_branch_name=github_branch_name,
    )

    content = {"body": f"Here is your IAM Policy.\n```json\n{iam_policy}\n```"}

    await github.add_comment_to_github_issue(
        github_access_token=github_access_token,
        repository_path=github_repository_name,
        issue_id=pull_request_id,
        content=content,
    )

    return iam_policy


async def run_from_cli(
    *,
    github_repository_name: str,
    github_branch_name: str,
):
    github_access_token = os.environ["GITHUB_TOKEN"]

    iam_policy = await generate_iam_policy_from_repository(
        github_access_token=github_access_token,
        cohere_api_key=COHERE_API_KEY,
        openai_api_key=OPENAI_API_KEY,
        github_repository_name=github_repository_name,
        github_branch_name=github_branch_name,
    )

    return iam_policy
