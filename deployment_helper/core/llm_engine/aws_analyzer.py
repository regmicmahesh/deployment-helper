import yaml
import json
import structlog
import typing as ty
from pydantic import BaseModel, Field

from deployment_helper.core.aws_iam_actions import AWS_SERVICE_NAMES, AWS_SERVICES_MAP
from deployment_helper.core.clients import openai


AWS_SDK_CALLS_PROMPT = """
You are an advanced code analysis assistant specialized in identifying and
extracting AWS SDK calls from source code. Your task is to analyze the provided
source code and return a list of all AWS SDK calls found, along with relevant
details about each call.

GUIDELINES:
- The actions should be in standard API Format of AWS such as ListTemplates,
  GetHostedZone, PassRole etc. If it's in boto3 python format such as list_templates,
  modify it to ListTemplates.

CONTEXTUAL INFORMATION:
- The source code may be written in various programming languages including
  Python, Java, and JavaScript.
- Focus on standard AWS SDKs such as Boto3 (Python), AWS SDK for Java,
  and AWS SDK for JavaScript.
- Refrain from using the resource ARNs and names from test or mock files.
  Discard it immediately.
- Use valid service names and actions only from the list below.
{aws_services}

INPUT:

File Path: {file_path}
Source Code:
```
{source_code}
```
"""


class AwsSdkCall(BaseModel):
    service: str = Field(description="Service name such as ses, sqs, s3 etc.")
    action: str = Field(
        description="Valid action for the service such as ListTemplates for ses, GetObject for s3 etc."
    )
    resource: str = Field(
        description="Resource ARN inferred from the SDK call. Use wildcards if can't be inferred. Don't use placeholders or example values.",
    )
    reasoning: str = Field(
        description="Reason behind picking this AWS statement. Add source code snippet as well if applicable from the original source code."
    )


class AwsSdkCalls(BaseModel):
    sdk_calls: list[AwsSdkCall]


async def find_aws_sdk_calls(
    *,
    logger=structlog.get_logger(),
    api_key: str,
    source_code: str,
    file_path: str,
    aws_services: dict[str, set[str]] = AWS_SERVICES_MAP,
) -> AwsSdkCalls:
    aws_services_with_actions_str = yaml.dump(aws_services, sort_keys=False)

    user_prompt = AWS_SDK_CALLS_PROMPT.format(
        source_code=source_code,
        file_path=file_path,
        aws_services=aws_services_with_actions_str,
    )
    response = await openai.invoke_structured(
        openai_api_key=api_key,
        user_prompt=user_prompt,
        response_format=AwsSdkCalls,
    )

    logger.info(
        "obtained aws sdk call statements used in the file",
        sdk_calls=response.sdk_calls,
    )

    return response


AWS_SERVICES_PROMPT = """
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


async def find_aws_service_names(
    *,
    logger=structlog.get_logger(),
    openai_api_key: str,
    source_code: str,
    file_path: str,
) -> AwsServices:
    aws_service_names_str = yaml.dump(AWS_SERVICE_NAMES)

    user_prompt = AWS_SERVICES_PROMPT.format(
        source_code=source_code,
        file_path=file_path,
        aws_service_names=aws_service_names_str,
    )
    response = await openai.invoke_structured(
        openai_api_key=openai_api_key,
        user_prompt=user_prompt,
        response_format=AwsServices,
    )

    logger.info(
        "obtained aws service names used",
        sdk_calls=response.service_names,
    )
    return response


REFINE_IAM_POLICY = """
I have an AWS IAM policy that contains placeholders and example values. Please
refine this policy by removing all placeholders or example values and ensuring
it is valid. The policy should maintain the original intent while being clear
and concise.

GUIDELINES:
1. The ARN should not include placeholder or examples such as "bucketName",
   "objectName" etc.
2. The ARN should not contain any templated variables such as ${{bucketName}},
   <bucket-name> etc. Instead replace it with "*" wildcards.
3. It should not contain duplicate actions or redundant statements.
4. If there is no actions in the policy, don't try to add any extra actions.


INPUT:
{policy}
"""


class AwsIamPolicy(BaseModel):
    policy_document: str


async def refine_iam_policy(
    *,
    logger=structlog.get_logger(),
    openai_api_key: str,
    iam_policy: ty.Any,
):
    iam_policy_str = json.dumps(iam_policy, indent=4)
    user_prompt = REFINE_IAM_POLICY.format(policy=iam_policy_str)

    response = await openai.invoke_structured(
        openai_api_key=openai_api_key,
        user_prompt=user_prompt,
        response_format=AwsIamPolicy,
    )

    return response


__ALL__ = ["find_aws_service_names", "AwsServices"]
