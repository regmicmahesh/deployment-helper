import typing as ty
import structlog
from openai import OpenAI

MODEL_NAME = "gpt-4o-mini"

T = ty.TypeVar("T")

logger = structlog.get_logger()


def invoke_structured(
    *,
    openai_api_key: str,
    user_prompt: str,
    response_format: type[T],
) -> T:
    logger.debug(
        "invoking openai api for structured output",
        response_format=response_format.__name__,
        user_prompt=user_prompt,
    )

    client = OpenAI(api_key=openai_api_key)

    chat_completion = client.beta.chat.completions.parse(
        messages=[
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        model=MODEL_NAME,
        n=1,
        response_format=response_format,
    )

    structured_response = chat_completion.choices[0].message.parsed

    logger.debug(
        "received response from openai api",
        response_format=response_format.__name__,
        user_prompt=user_prompt,
        structured_response=structured_response,
    )

    return structured_response  # type: ignore
