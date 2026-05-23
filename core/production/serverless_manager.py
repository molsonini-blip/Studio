"""
RunPod Serverless client. Submits SadTalker jobs to a pre-deployed endpoint.
No pod lifecycle management — endpoint auto-scales to zero when idle.

Requires env vars:
  RUNPOD_API_KEY         RunPod API key
  RUNPOD_ENDPOINT_ID     Serverless endpoint ID (e.g. "abc123xyz")
"""
from __future__ import annotations

import base64
import os
import random
import time
from pathlib import Path

import requests

RUNPOD_BASE = "https://api.runpod.ai/v2"


class ServerlessManager:
    def __init__(
        self,
        api_key: str | None = None,
        endpoint_id: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("RUNPOD_API_KEY")
        self.endpoint_id = endpoint_id or os.environ.get("RUNPOD_ENDPOINT_ID")
        if not self.api_key:
            raise RuntimeError("RUNPOD_API_KEY not set")
        if not self.endpoint_id:
            raise RuntimeError("RUNPOD_ENDPOINT_ID not set")

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def submit_job(self, portrait: Path, audio: Path, anchor_id: str) -> str:
        """Submit a render job. Returns job_id."""
        payload = {
            "input": {
                "anchor_id": anchor_id,
                "portrait_b64": base64.b64encode(portrait.read_bytes()).decode(),
                "audio_b64": base64.b64encode(audio.read_bytes()).decode(),
                "pose_style": random.randint(0, 45),
            }
        }
        resp = requests.post(
            f"{RUNPOD_BASE}/{self.endpoint_id}/run",
            json=payload,
            headers=self._headers,
            timeout=30,
        )
        resp.raise_for_status()
        job_id = resp.json()["id"]
        print(f"[serverless] Job submitted: {job_id} ({anchor_id})")
        return job_id

    def wait_for_job(
        self,
        job_id: str,
        timeout: int = 1800,
        poll_interval: int = 10,
    ) -> dict:
        """Poll until job completes. Returns output dict."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = requests.get(
                f"{RUNPOD_BASE}/{self.endpoint_id}/status/{job_id}",
                headers=self._headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")

            if status == "COMPLETED":
                output = data.get("output", {})
                if "error" in output:
                    raise RuntimeError(f"Worker error: {output['error']}")
                return output
            elif status == "FAILED":
                raise RuntimeError(f"Job {job_id} failed: {data}")
            elif status in ("IN_QUEUE", "IN_PROGRESS"):
                print(f"[serverless] {job_id}: {status}...")
                time.sleep(poll_interval)
            else:
                print(f"[serverless] {job_id}: unknown status {status}, waiting...")
                time.sleep(poll_interval)

        raise TimeoutError(f"Job {job_id} timed out after {timeout}s")

    def render(self, portrait: Path, audio: Path, anchor_id: str, out_path: Path) -> Path:
        """Submit + wait + save MP4. Returns out_path."""
        job_id = self.submit_job(portrait, audio, anchor_id)
        output = self.wait_for_job(job_id)
        mp4_bytes = base64.b64decode(output["mp4_b64"])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(mp4_bytes)
        print(f"[serverless] Saved: {out_path} ({len(mp4_bytes)//1024} KB)")
        return out_path

    def render_all(
        self,
        jobs: list[dict],
        episode_dir: Path,
    ) -> list[Path]:
        """
        Submit all jobs in parallel, then collect results.
        jobs: list of {anchor_id, portrait: Path, audio: Path}
        Returns list of output MP4 paths in same order.
        """
        # Submit all at once
        job_ids = []
        for job in jobs:
            jid = self.submit_job(job["portrait"], job["audio"], job["anchor_id"])
            job_ids.append(jid)

        # Collect results
        results = []
        for job, jid in zip(jobs, job_ids):
            out_path = episode_dir / f"{job['anchor_id']}_seg.mp4"
            output = self.wait_for_job(jid)
            mp4_bytes = base64.b64decode(output["mp4_b64"])
            out_path.write_bytes(mp4_bytes)
            print(f"[serverless] {job['anchor_id']} -> {out_path.name} ({len(mp4_bytes)//1024} KB)")
            results.append(out_path)

        return results
