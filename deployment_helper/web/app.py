import hmac
import hashlib


from sanic import Sanic, json
from sanic.request import Request
from sanic.response import HTTPResponse, text
from sanic.exceptions import BadRequest, HeaderNotFound

from deployment_helper.core import run_with_github_apps_installation

SECRET_TOKEN = b"regmicmahesh"

app = Sanic("DeploymentHelperApp")


@app.get("/healthz")
async def healthz(request: Request):
    return text("Server is up and running.")


@app.on_request
async def verify_signature(request: Request) -> HTTPResponse | None:
    signature_header = request.headers.get("x-hub-signature-256")

    payload_body = request.body

    if not signature_header:
        raise HeaderNotFound("x-hub-signature-256 header is missing")

    hash_object = hmac.new(
        SECRET_TOKEN,
        msg=payload_body,
        digestmod=hashlib.sha256,
    )

    expected_signature = "sha256=" + hash_object.hexdigest()
    if not hmac.compare_digest(expected_signature, signature_header):
        raise BadRequest("invalid signature received")

    print("request verified.")


@app.post("/events")
async def process_events(request: Request) -> HTTPResponse:
    data = request.json

    print(data["action"])

    if data["action"] not in ("edited", "opened", "reopened", "synchronize"):
        return json({"ack": True, "op": "no-op"})

    pull_request = data["pull_request"]

    pull_request_head = pull_request["head"]

    repository_branch = pull_request_head["ref"]
    repository_name = pull_request_head["repo"]["full_name"]

    await run_with_github_apps_installation(
        github_repository_name=repository_name,
        github_branch_name=repository_branch,
        pull_request_id=data["number"],
    )

    return json({"ack": True, "op": "no-op"})
