import structlog
import yaml
from pydantic import BaseModel, Field

from deployment_helpers.clients.openai import invoke_structured
from deployment_helpers.llm.aws.helpers import AWS_SERVICES_MAP


PROMPT = """
You are an advanced code analysis assistant specialized in identifying and
extracting AWS SDK calls from source code. Your task is to analyze the provided
source code and return a list of all AWS SDK calls found, along with relevant
details about each call.

**Contextual Information:**
- The source code may be written in various programming languages including
  Python, Java, and JavaScript.
- Focus on standard AWS SDKs such as Boto3 (Python), AWS SDK for Java,
  and AWS SDK for JavaScript.
- Refrain from using the resource ARNs and names from test files.
- Use valid service names and actions only from the list below.
{aws_services}

INPUT:

File Path: {file_path}
Source Code:
```
{source_code}
```
"""


class AwsStatement(BaseModel):
    service: str = Field(description="Service Name such as ses, sqs, s3 etc.")
    action: str = Field(
        description="Valid Action for the Service such as ListTemplates for ses, GetObject for s3 etc."
    )
    resource: str = Field(
        description="Resource ARN inferred from the SDK call. Use wildcards if can't be inferred.",
    )
    reasoning: str = Field(
        description="Reason behind picking this AWS Statement. Add source code snippet as well if applicable from the original source code"
    )


class AwsSdkCalls(BaseModel):
    aws_statements: list[AwsStatement]


def find_aws_sdk_calls(
    *,
    logger=structlog.get_logger(),
    api_key: str,
    source_code: str,
    file_path: str,
    aws_services: dict[str, set[str]] = AWS_SERVICES_MAP,
) -> AwsSdkCalls:
    aws_services_with_actions_str = yaml.dump(aws_services, sort_keys=False)

    user_prompt = PROMPT.format(
        source_code=source_code,
        file_path=file_path,
        aws_services=aws_services_with_actions_str,
    )
    response = invoke_structured(
        openai_api_key=api_key,
        user_prompt=user_prompt,
        response_format=AwsSdkCalls,
    )

    logger.info(
        "obtained aws sdk call statements used in the file",
        sdk_calls=response.aws_statements,
    )

    return response
