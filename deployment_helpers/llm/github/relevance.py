import structlog
import yaml
from dataclasses import asdict

from deployment_helpers.clients.github import GithubFile
from deployment_helpers.clients.cohere import rerank_documents


FILE_RELEVANCE_RERANKER_PROMPT = """
AWS SDK function calls (boto3, aws-go-sdk, awssdkv3) and wrapper functions
that interact with AWS services.
"""


def find_relevant_github_source_files(
    *,
    logger=structlog.get_logger(),
    reranker_api_key: str,
    source_code_files: list[GithubFile],
    top_n: int | None = None,
    relevance_score_threshold: float = 0.1,
) -> list[GithubFile]:
    # Convert all files to YAML because cohere has better accuracy with it.
    plain_files = []
    for file in source_code_files:
        file_dict = asdict(file)
        plain_files.append(yaml.dump(file_dict, sort_keys=False))

    # Rerank files using cohere reranker.
    reranked_texts = rerank_documents(
        api_key=reranker_api_key,
        query=FILE_RELEVANCE_RERANKER_PROMPT,
        documents=plain_files,
        top_n=top_n,
        relevance_score_threshold=relevance_score_threshold,
    )

    reranked_files: list[GithubFile] = []
    for text in reranked_texts:
        file_dict = yaml.safe_load(text.content)
        reranked_files.append(GithubFile(**file_dict))

    return reranked_files
