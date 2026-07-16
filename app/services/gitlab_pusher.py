"""
gitlab_pusher.py
----------------
Push the formatted Markdown file to a GitLab repository.
Uses python-gitlab with a Personal Access Token (PAT).

Output path in repo: {GITLAB_OUTPUT_PATH}/{YYYY-MM-DD}/{job_id}.md
"""

import logging
from datetime import datetime, timezone

from app.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()


class GitLabPusher:
    """
    Push a Markdown file to a GitLab repository.

    Configuration (via .env):
        GITLAB_URL         URL of the GitLab instance (default: https://gitlab.com)
        GITLAB_TOKEN       Personal Access Token with api/write_repository scope
        GITLAB_PROJECT_ID  Project ID or "namespace/project-name"
        GITLAB_BRANCH      branch to commit to (default: main)
        GITLAB_OUTPUT_PATH folder prefix inside the repo (default: outputs)
    """

    def push(
        self,
        job_id:    str,
        file_name: str,
        markdown:  str,
    ) -> str:
        """
        Create or update a file in the GitLab repo.

        Returns
        -------
        str : URL of the committed file on GitLab.
        """
        if not settings.gitlab_token or not settings.gitlab_project_id:
            logger.warning("GitLab credentials not configured — skipping push.")
            return ""

        try:
            import gitlab
            from gitlab.exceptions import GitlabGetError
        except ImportError:
            raise ImportError(
                "python-gitlab is not installed. Run: pip install python-gitlab"
            )

        gl = gitlab.Gitlab(url=settings.gitlab_url, private_token=settings.gitlab_token)
        project = gl.projects.get(settings.gitlab_project_id)

        date_folder = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        repo_path   = f"{settings.gitlab_output_path}/{date_folder}/{job_id}.md"
        branch      = settings.gitlab_branch
        message     = f"feat: add processed document [{file_name}] (job {job_id})"

        try:
            # Try to get existing file (update scenario)
            existing = project.files.get(file_path=repo_path, ref=branch)
            existing.content = markdown
            existing.save(branch=branch, commit_message=message)
            commit_url = f"{project.web_url}/-/blob/{branch}/{repo_path}"
            logger.info(
                "Updated existing file in GitLab: %s → %s",
                repo_path, commit_url,
            )
        except GitlabGetError as exc:
            if exc.response_code == 404:
                # File does not exist yet — create it
                project.files.create({
                    'file_path': repo_path,
                    'branch': branch,
                    'content': markdown,
                    'commit_message': message,
                })
                commit_url = f"{project.web_url}/-/blob/{branch}/{repo_path}"
                logger.info(
                    "Created new file in GitLab: %s → %s",
                    repo_path, commit_url,
                )
            else:
                raise

        logger.info("GitLab push complete: %s", commit_url)
        return commit_url
