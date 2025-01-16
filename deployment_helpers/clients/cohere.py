import cohere
import structlog
from dataclasses import dataclass

RERANKER_MODEL_NAME = "rerank-v3.5"

logger = structlog.get_logger()


@dataclass
class RankedText:
    rank: int
    content: str
    relevance_score: float


def rerank_documents(
    *,
    api_key: str,
    query: str,
    documents: list[str],
    top_n: int | None = None,
    relevance_score_threshold: float,
) -> list[RankedText]:
    logger.debug(
        "invoking cohere api for reranking",
        document_count=len(documents),
        query=query[:100],
    )

    co = cohere.ClientV2(api_key=api_key)  # type: ignore

    response = co.rerank(
        model=RERANKER_MODEL_NAME,
        query=query,
        documents=documents,
        top_n=top_n,
    )

    ranked_texts: list[RankedText] = []

    for result in response.results:
        if result.relevance_score < relevance_score_threshold:
            continue

        ranked_text = RankedText(
            rank=result.index,
            content=documents[result.index],
            relevance_score=result.relevance_score,
        )
        ranked_texts.append(ranked_text)

    return ranked_texts
