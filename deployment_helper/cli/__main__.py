import asyncio
import argparse

from deployment_helper.core import run_from_cli

parser = argparse.ArgumentParser(
    prog="DeploymentHelperApp",
    description="Constructs iam policy based on your source code.",
)

parser.add_argument(
    "--repository", required=True, help="Github Repository for which you want to run."
)
parser.add_argument(
    "--branch",
    required=False,
    default="main",
    help="Github branch name. default: 'main'",
)


def main():
    args = parser.parse_args()

    iam_policy = asyncio.run(run_from_cli(
        github_repository_name=args.repository,
        github_branch_name=args.branch,
    ))

    print("IAM Policy Generated:")

    print(iam_policy)


if __name__ == "__main__":
    main()

