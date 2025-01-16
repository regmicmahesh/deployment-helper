import os
import structlog
import logging

from deployment_helpers.clients.github import get_files
from deployment_helpers.llm.aws.helpers import (
    AWS_SERVICES_MAP,
    is_valid_aws_service_action,
)
from deployment_helpers.llm.aws.service_actions import find_aws_sdk_calls
from deployment_helpers.llm.aws.service_names import find_aws_service_names
from deployment_helpers.llm.github.relevance import find_relevant_github_source_files


GITHUB_ACCESS_TOKEN = os.environ["GITHUB_TOKEN"]
COHERE_API_KEY = os.environ["COHERE_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

GITHUB_REPOSITORY_NAME = "zen4ever/route53manager"
GITHUB_BRANCH_NAME = "master"

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

logger = structlog.get_logger(service="deployment-helper")


def is_source_code(file_path: str):
    source_code_ext = [
        ".py",
        ".js",
        ".ts",
        ".rb",
        ".java",
        ".go",
        ".md",
    ]

    return any(file_path.endswith(ext) for ext in source_code_ext)


logger = logger.bind(
    repository_name=GITHUB_REPOSITORY_NAME,
    branch_name=GITHUB_BRANCH_NAME,
)

logger.info("obtaining files from github")

github_files = get_files(
    logger=logger,
    github_access_token=GITHUB_ACCESS_TOKEN,
    repository_path=GITHUB_REPOSITORY_NAME,
    branch_name=GITHUB_BRANCH_NAME,
    file_filter=is_source_code,
)

logger = logger.bind(github_files_count=len(github_files))
logger.info("obtained files from github successfully")

logger.info("filtering out irrelevant files using reranker")
relevant_source_files = find_relevant_github_source_files(
    logger=logger,
    reranker_api_key=COHERE_API_KEY,
    source_code_files=github_files,
    top_n=15,
    relevance_score_threshold=0.01,
)

logger = logger.bind(relevant_files_count=len(relevant_source_files))
logger.info("relevant source files filtered successfully")

used_aws_services: set[str] = set()
for file in relevant_source_files:
    logger = logger.bind(file_path=file.path)
    logger.info("processing relevant source file")

    aws_services = find_aws_service_names(
        logger=logger,
        api_key=OPENAI_API_KEY,
        source_code=file.content,
        file_path=file.path,
    )

    relevant_aws_services: dict[str, set[str]] = {}

    for aws_service in aws_services.service_names:
        relevant_aws_services[aws_service] = AWS_SERVICES_MAP[aws_service]

    sdk_calls = find_aws_sdk_calls(
        logger=logger,
        api_key=os.environ["OPENAI_API_KEY"],
        source_code=file.content,
        file_path=file.path,
        aws_services=relevant_aws_services,
    )

    logger.bind(aws_statements=sdk_calls.aws_statements)

    for stmt in sdk_calls.aws_statements:
        if not is_valid_aws_service_action(stmt.service, stmt.action):
            logger.error(
                "invalid aws service action",
                invalid_action=stmt.action,
                invalid_service=stmt.service,
            )
        else:
            ...
    logger.info("processed successfully relevant source file")
