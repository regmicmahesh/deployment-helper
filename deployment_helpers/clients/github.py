import typing as ty
from dataclasses import dataclass, field
import base64
import requests
import structlog

GITHUB_API_URL = "https://api.github.com"


@dataclass
class GithubFile:
    path: str
    url: str
    size: int | None = field(default=None)
    content: str = field(default="")


def _get_file_content_by_path(
    *,
    logger=structlog.get_logger(),
    access_token: str,
    repository_path: str,
    branch_name: str,
    path: str,
) -> str:
    logger = logger.bind(path=path)
    logger.info("invoking github api to obtain file content")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
    }

    # https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28
    base_url = (
        f"{GITHUB_API_URL}/repos/{repository_path}/contents/{path}?ref={branch_name}"
    )

    response = requests.get(base_url, headers=headers)
    response.raise_for_status()

    logger.debug(
        "obtained file content response from github api",
        response=response.json(),
        status_code=response.status_code,
    )

    if isinstance(response.json(), dict):
        content_encoded = response.json()["content"]
        try:
            return base64.b64decode(content_encoded).decode("utf-8")
        except UnicodeDecodeError:
            pass

    return ""


def get_github_files(
    *,
    logger=structlog.get_logger(),
    github_access_token: str,
    repository_path: str,
    branch_name: str = "main",
    file_filter: ty.Callable | None = None,
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

    response = requests.get(base_url, headers=headers)
    response.raise_for_status()

    data = response.json()

    logger.info(
        "obtained file list from github api",
        status_code=response.status_code,
    )

    github_files = []
    for file in data["tree"]:
        # Skip folders.
        if file["type"] == "tree":
            continue

        # If file_filter is defined, then exclude which doesn't pass the
        # predicate.
        if file_filter and not file_filter(file["path"]):
            logger.debug("skipping file because of file filter", file_path=file["path"])
            continue

        content = _get_file_content_by_path(
            logger=logger,
            access_token=github_access_token,
            repository_path=repository_path,
            branch_name=branch_name,
            path=file["path"],
        )

        github_file = GithubFile(
            path=file["path"], size=file["size"], url=file["url"], content=content
        )

        github_files.append(github_file)

    return github_files
