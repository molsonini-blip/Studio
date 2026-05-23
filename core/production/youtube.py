"""
YouTube upload stub. Implement with google-api-python-client when account is ready.

To enable:
  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
  Follow OAuth2 setup at: https://developers.google.com/youtube/v3/guides/uploading_a_video
"""
from __future__ import annotations

from pathlib import Path


def upload_to_youtube(
    video_path: Path,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    category_id: str = "25",  # 25 = News & Politics
    privacy: str = "public",
) -> str | None:
    """
    Upload video to YouTube. Returns video URL or None if stub/disabled.

    Stub implementation — logs intent and returns None.
    Replace body with real implementation once YouTube account + OAuth2 are set up.
    """
    print(f"[youtube] STUB — would upload: {video_path.name}")
    print(f"[youtube]   title: {title}")
    print(f"[youtube]   privacy: {privacy}")
    print(f"[youtube]   (YouTube account not yet configured)")
    return None
