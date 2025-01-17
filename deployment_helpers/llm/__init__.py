import asyncio
import json
import typing as ty
import structlog
from collections import defaultdict

from deployment_helpers.aws_data import AWS_SERVICES_MAP
from deployment_helpers.clients.github import get_github_files
from deployment_helpers.llm.aws import (
    AwsStatement,
    find_aws_sdk_calls,
    find_aws_service_names,
    refine_iam_policy,
)
from deployment_helpers.llm.relevance import find_relevant_github_source_files


def _is_source_code(file_path: str):
    source_code_ext = {".py", ".js", ".ts", ".rb", ".java", ".go", ".md"}

    return any(file_path.endswith(ext) for ext in source_code_ext)


def _is_valid_aws_service_action(
    *,
    logger=structlog.get_logger(),
    service: str,
    action: str,
) -> bool:
    """Checks if the action is valid for the given AWS service."""
    try:
        return action in AWS_SERVICES_MAP.get(service, [])
    except KeyError as e:
        logger.error(
            "Error validating AWS service action",
            error=str(e),
            service=service,
            action=action,
        )
        return False


async def generate_iam_policy_from_repository(
    *,
    logger=structlog.get_logger(),
    github_access_token: str,
    cohere_api_key: str,
    openai_api_key: str,
    github_repository_name: str,
    github_branch_name: str,
) -> str:
    """Processes GitHub repository, filtering relevant source files and processing them."""

    logger = logger.bind(
        repository_name=github_repository_name,
        branch_name=github_branch_name,
    )
    logger.info("obtaining files from github")

    github_files = await get_github_files(
        logger=logger,
        github_access_token=github_access_token,
        repository_path=github_repository_name,
        branch_name=github_branch_name,
        file_filter=_is_source_code,
    )

    logger = logger.bind(github_files_count=len(github_files))
    logger.info("obtained files from github successfully")

    logger.info("filtering out irrelevant files using reranker")
    relevant_source_files = find_relevant_github_source_files(
        logger=logger,
        reranker_api_key=cohere_api_key,
        source_code_files=github_files,
        top_n=15,
        relevance_score_threshold=0.01,
    )

    logger = logger.bind(relevant_files_count=len(relevant_source_files))
    logger.info("relevant source files filtered successfully")

    tasks = []

    for file in relevant_source_files:
        tasks.append(
            _get_relevant_aws_statements_from_file(
                logger=logger,
                openai_api_key=openai_api_key,
                file_path=file.path,
                file_content=file.content,
            )
        )

    aws_statements = await asyncio.gather(*tasks)

    actions_dict: dict[str, set[str]] = defaultdict(set)
    for stmt in aws_statements:
        actions_dict[stmt.resource].add(f"{stmt.service}:{stmt.action}")

    iam_policy = _construct_iam_policy(
        logger=logger,
        actions_dict=actions_dict,
    )

    refined_iam_policy = await refine_iam_policy(
        logger=logger,
        openai_api_key=openai_api_key,
        iam_policy=iam_policy,
    )

    return json.dumps(refined_iam_policy.policy_document, indent=4)


def _construct_iam_policy(
    *,
    logger=structlog.get_logger(),
    actions_dict: dict[str, set[str]],
) -> ty.Any:
    logger.info("final list of actions", actions_dict=actions_dict)

    iam_policy = {
        "Version": "2012-10-17",
        "Statement": [],
    }

    for resource, actions in actions_dict.items():
        iam_policy["Statement"].append(
            {
                "Effect": "Allow",
                "Action": list(actions),
                "Resource": resource,
            }
        )

    return iam_policy


async def _get_relevant_aws_statements_from_file(
    *,
    logger=structlog.get_logger(),
    openai_api_key: str,
    file_path: str,
    file_content: str,
) -> list[AwsStatement]:
    logger = logger.bind(file_path=file_path)
    logger.info("processing relevant source file")

    aws_services = await find_aws_service_names(
        logger=logger,
        openai_api_key=openai_api_key,
        source_code=file_content,
        file_path=file_path,
    )

    relevant_aws_services: dict[str, set[str]] = {}
    for aws_service in aws_services.service_names:
        if aws_service not in AWS_SERVICES_MAP:
            # TODO: add logging behaviour
            continue
        relevant_aws_services[aws_service] = AWS_SERVICES_MAP[aws_service]

    sdk_calls = await find_aws_sdk_calls(
        logger=logger,
        api_key=openai_api_key,
        source_code=file_content,
        file_path=file_path,
        aws_services=relevant_aws_services,
    )

    logger.bind(aws_statements=sdk_calls.aws_statements)

    for idx, stmt in enumerate(sdk_calls.aws_statements):
        if not _is_valid_aws_service_action(
            logger=logger,
            service=stmt.service,
            action=stmt.action,
        ):
            logger.error(
                "invalid aws service action",
                invalid_action=stmt.action,
                invalid_service=stmt.service,
            )
            del sdk_calls.aws_statements[idx]
            continue

    return sdk_calls.aws_statements
