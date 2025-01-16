import os
import structlog
import logging

from deployment_helpers.llm import get_iam_policy_from_repository

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)


GITHUB_ACCESS_TOKEN = os.environ["GITHUB_TOKEN"]
COHERE_API_KEY = os.environ["COHERE_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

GITHUB_REPOSITORY_NAME = "awslabs/aws-simple-ec2-cli"
GITHUB_BRANCH_NAME = "main"


def main():
    iam_policy = get_iam_policy_from_repository(
        github_access_token=GITHUB_ACCESS_TOKEN,
        cohere_api_key=COHERE_API_KEY,
        openai_api_key=OPENAI_API_KEY,
        github_repository_name=GITHUB_REPOSITORY_NAME,
        github_branch_name=GITHUB_BRANCH_NAME,
    )

    print(iam_policy)


if __name__ == "__main__":
    main()
