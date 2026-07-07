"""
github_pusher.py
----------------
Push the formatted Markdown file to a GitHub repository.
Uses PyGitHub with a Personal Access Token (PAT).

Output path in repo: {GITHUB_OUTPUT_PATH}/{YYYY-MM-DD}/{job_id}.md
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()


class GitHubPusher:
    """
    Push a Markdown file to a GitHub repository.

    Configuration (via .env):
        GITHUB_TOKEN       Personal Access Token with repo scope
        GITHUB_REPO        "owner/repo-name"
        GITHUB_BRANCH      branch to commit to (default: main)
        GITHUB_OUTPUT_PATH folder prefix inside the repo (default: outputs)
    """

    def push(
        self,
        job_id:    str,
        file_name: str,
        markdown:  str,
    ) -> str:
        """
        Create or update a file in the GitHub repo.

        Returns
        -------
        str : URL of the committed file on GitHub.
        """
        if not settings.github_token or not settings.github_repo:
            logger.warning("GitHub credentials not configured — skipping push.")
            return ""

        try:
            from github import Github, GithubException
        except ImportError:
            raise ImportError(
                "PyGitHub is not installed. Run: pip install PyGithub"
            )

        g    = Github(settings.github_token)
        repo = g.get_repo(settings.github_repo)

        date_folder = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        repo_path   = f"{settings.github_output_path}/{date_folder}/{job_id}.md"
        branch      = settings.github_branch
        message     = f"feat: add processed document [{file_name}] (job {job_id})"

        try:
            # Try to get existing file (update scenario)
            existing = repo.get_contents(repo_path, ref=branch)
            result = repo.update_file(
                path=repo_path,
                message=message,
                content=markdown,
                sha=existing.sha,
                branch=branch,
            )
            logger.info(
                "Updated existing file in GitHub: %s → %s",
                repo_path, result["commit"].html_url,
            )
        except GithubException as exc:
            if exc.status == 404:
                # File does not exist yet — create it
                result = repo.create_file(
                    path=repo_path,
                    message=message,
                    content=markdown,
                    branch=branch,
                )
                logger.info(
                    "Created new file in GitHub: %s → %s",
                    repo_path, result["commit"].html_url,
                )
            else:
                raise

        commit_url = result["commit"].html_url
        logger.info("GitHub push complete: %s", commit_url)
        return commit_url
