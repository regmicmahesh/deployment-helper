import structlog
import yaml
from pydantic import BaseModel

from deployment_helpers.clients.openai import invoke_structured
from deployment_helpers.llm.aws.helpers import AWS_SERVICE_NAMES

logger = structlog.get_logger()


PROMPT = """
You are an advanced code analysis assistant specialized in identifying and
extracting AWS SDK calls from source code. Your task is to analyze the provided
source code and return a list of all AWS SDK calls found, along with relevant
details about each call.

Analyze the source code and extract all unique AWS service names that are used
via the AWS SDK. Focus on instances where the SDK is invoked either directly
(e.g., new AWS.ServiceName(), AWS.ServiceName()) or through method calls
like service.method() (e.g., s3.getObject(), iam.createRole(), lambda.invoke(),
dynamodb.query()). Be sure to also detect custom function wrappers that may
abstract AWS SDK calls, such as uploadToS3(), createIAMRole(),
invokeLambdaFunction(), etc., even if the SDK calls are hidden within them.
The goal is to identify and list AWS service names like s3, iam, lambda,
dynamodb, route53, sns, ec2, sqs, rds, and any other AWS service used in the
code.

**Contextual Information:**
- The source code may be written in various programming languages including
  Python, Java, and JavaScript.
- Focus on standard AWS SDKs such as Boto3 (Python), AWS SDK for Java,
  and AWS SDK for JavaScript.
- Use only the service names from the list below.
{aws_service_names}

INPUT:

File Path: {file_path}
Source Code:
```
{source_code}
```
"""


class AwsServices(BaseModel):
    service_names: list[str]


def find_aws_service_names(
    *,
    logger=structlog.get_logger(),
    api_key: str,
    source_code: str,
    file_path: str,
) -> AwsServices:
    aws_service_names_str = yaml.dump(AWS_SERVICE_NAMES)

    user_prompt = PROMPT.format(
        source_code=source_code,
        file_path=file_path,
        aws_service_names=aws_service_names_str,
    )
    response = invoke_structured(
        openai_api_key=api_key,
        user_prompt=user_prompt,
        response_format=AwsServices,
    )

    logger.info(
        "obtained aws service names used",
        sdk_calls=response.service_names,
    )
    return response
