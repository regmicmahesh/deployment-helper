import time
import typing as ty
import asyncio
import base64

import structlog
import aiohttp
from jwt import JWT, jwk_from_pem

GITHUB_API_URL = "https://api.github.com"


def _create_jwt_key(jwt_private_key: bytes, client_id: str) -> str:
    instance = JWT()

    signing_key = jwk_from_pem(jwt_private_key)

    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,
        "iss": client_id,
    }

    encoded_jwt = instance.encode(payload, signing_key, alg="RS256")

    return encoded_jwt


async def get_github_apps_access_token(
    *,
    repository_path: str,
    jwt_private_key: bytes,
    client_id: str,
) -> str:
    jwt_key = _create_jwt_key(jwt_private_key, client_id)

    installation_info_url = f"{GITHUB_API_URL}/repos/{repository_path}/installation"

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {jwt_key}",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(installation_info_url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

        installation_id = data["id"]

        installation_token_url = (
            f"{GITHUB_API_URL}/app/installations/{installation_id}/access_tokens"
        )

        async with session.post(installation_token_url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

    return data["token"]


async def add_comment_to_github_issue(
    *,
    github_access_token: str,
    repository_path: str,
    issue_id: int,
    content: ty.Any,
):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_access_token}",
    }

    base_url = f"{GITHUB_API_URL}/repos/{repository_path}/issues/{issue_id}/comments"

    async with aiohttp.ClientSession() as session:
        async with session.post(
            base_url,
            headers=headers,
            json=content,
        ) as response:
            response.raise_for_status()


class GithubFile(ty.TypedDict):
    path: str
    url: str
    size: ty.NotRequired[int]
    content: ty.NotRequired[str]


async def _fetch_github_file(
    *,
    logger=structlog.get_logger(),
    github_access_token: str,
    repository_path: str,
    branch_name: str,
    file_path: str,
    file_size: int,
    file_url: str,
) -> GithubFile:
    logger = logger.bind(path=file_path)
    logger.info("invoking github api to obtain file content")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_access_token}",
    }

    # https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28
    base_url = f"{GITHUB_API_URL}/repos/{repository_path}/contents/{file_path}?ref={branch_name}"

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

    logger.debug(
        "obtained file content response from github api",
        response=data,
        status_code=response.status,
    )

    github_file: GithubFile = {
        "path": file_path,
        "size": file_size,
        "url": file_url,
    }

    if isinstance(data, dict):
        content_encoded = data["content"]
        try:
            github_file["content"] = base64.b64decode(content_encoded).decode("utf-8")
        except UnicodeDecodeError:
            pass

    return github_file


async def fetch_github_repository_files(
    *,
    logger=structlog.get_logger(),
    github_access_token: str,
    repository_path: str,
    branch_name: str = "main",
    file_filter: ty.Callable = lambda _: True,
) -> list[GithubFile]:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_access_token}",
    }

    # https://docs.github.com/en/rest/git/trees?apiVersion=2022-11-28#get-a-tree
    base_url = (
        f"{GITHUB_API_URL}/repos/{repository_path}/git/trees/"
        f"{branch_name}?recursive=1"
    )

    logger.info(
        "obtaining file list from github api",
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

        logger.info(
            "obtained file list from github api",
            status_code=response.status,
        )

        github_files = await asyncio.gather(
            *(
                _fetch_github_file(
                    logger=logger,
                    github_access_token=github_access_token,
                    repository_path=repository_path,
                    branch_name=branch_name,
                    file_path=file["path"],
                    file_size=file["size"],
                    file_url=file["url"],
                )
                for file in data["tree"]
                if (file["type"] != "tree") and file_filter(file["path"])
            )
        )

        return github_files
