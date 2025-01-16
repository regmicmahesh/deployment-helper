import requests
import json

IAM_POLICIES_URL = "https://awspolicygen.s3.amazonaws.com/js/policies.js"


def _extract_all_iam_service_actions():
    resp = requests.get(IAM_POLICIES_URL)

    # Strip out the part which is "app.PolicyEditorConfig={"
    valid_text = resp.text[23:]

    resp_json = json.loads(valid_text)

    service_map = resp_json["serviceMap"]

    services: dict[str, set[str]] = {}
    for _, svc_item in service_map.items():
        services[svc_item["StringPrefix"]] = set(svc_item["Actions"])

    return services


AWS_SERVICES_MAP = _extract_all_iam_service_actions()

AWS_SERVICE_NAMES = [el for el in AWS_SERVICES_MAP]


def is_valid_aws_service_action(service: str, action: str) -> bool:
    try:
        return action in AWS_SERVICES_MAP.get(service, [])
    except Exception:
        return False
