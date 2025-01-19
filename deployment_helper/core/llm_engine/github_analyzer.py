import structlog
import yaml

from deployment_helper.core.aws_iam_actions import AWS_SERVICES_MAP
from deployment_helper.core.clients import github
from deployment_helper.core.clients import cohere


PROMPT = """
AWS SDK function calls (boto3, aws-go-sdk, awssdkv3) and wrapper functions
that interact with AWS services.
{aws_services}
""".format(aws_services=yaml.dump(AWS_SERVICES_MAP))


def find_relevant_github_source_files(
    *,
    logger=structlog.get_logger(),
    reranker_api_key: str,
    source_code_files: list[github.GithubFile],
    top_n: int | None = None,
    relevance_score_threshold: float = 0.1,
) -> list[github.GithubFile]:
    plain_files = [yaml.dump(f, sort_keys=False) for f in source_code_files]

    # Rerank files using cohere reranker.
    reranked_texts = cohere.rerank_documents(
        logger=logger,
        api_key=reranker_api_key,
        query=PROMPT,
        documents=plain_files,
        top_n=top_n,
        relevance_score_threshold=relevance_score_threshold,
    )

    reranked_files: list[github.GithubFile] = []
    for text in reranked_texts:
        file_dict = yaml.safe_load(text["content"])
        github_file = github.GithubFile(**file_dict)
        reranked_files.append(github_file)

    return reranked_files


__ALL__ = ["find_relevant_github_source_files"]
