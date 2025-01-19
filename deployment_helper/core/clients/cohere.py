import typing as ty
import cohere
import structlog

RERANKER_MODEL_NAME = "rerank-v3.5"


class RankedText(ty.TypedDict):
    rank: int
    content: str
    relevance_score: float


def rerank_documents(
    *,
    logger=structlog.get_logger(),
    api_key: str,
    query: str,
    documents: list[str],
    top_n: int | None = None,
    relevance_score_threshold: float,
) -> list[RankedText]:
    logger.info(
        "invoking cohere api for reranking",
        document_count=len(documents),
    )

    co = cohere.ClientV2(api_key=api_key)  # type: ignore

    response = co.rerank(
        model=RERANKER_MODEL_NAME,
        query=query,
        documents=documents,
        top_n=top_n,
    )

    ranked_texts = [
        RankedText(
            rank=r.index, content=documents[r.index], relevance_score=r.relevance_score
        )
        for r in response.results
        if r.relevance_score >= relevance_score_threshold
    ]

    return ranked_texts
