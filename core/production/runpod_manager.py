"""
RunPod pod lifecycle management: create → wait for SSH → use → terminate.
Requires env var RUNPOD_API_KEY.
"""
from __future__ import annotations

import os
import time
import socket
from pathlib import Path
from typing import Callable

import requests
import paramiko

RUNPOD_API = "https://api.runpod.io/graphql"
DEFAULT_GPU = "NVIDIA GeForce RTX 4090"
GPU_FALLBACKS = [
    "NVIDIA GeForce RTX 4090",
    "NVIDIA RTX A5000",
    "NVIDIA RTX A4000",
    "NVIDIA A10G",
    "NVIDIA GeForce RTX 3090",
    "NVIDIA A40",
]
DEFAULT_IMAGE = "runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04"
DISK_GB = 50
POD_NAME = "studio-render"


def _gql(query: str, variables: dict, api_key: str) -> dict:
    resp = requests.post(
        RUNPOD_API,
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"RunPod API error: {data['errors']}")
    return data["data"]


CREATE_POD_MUTATION = """
mutation CreatePod($input: PodFindAndDeployOnDemandInput!) {
  podFindAndDeployOnDemand(input: $input) {
    id
    desiredStatus
    imageName
    machineId
  }
}
"""

GET_POD_QUERY = """
query GetPod($podId: String!) {
  pod(input: { podId: $podId }) {
    id
    desiredStatus
    runtime {
      ports {
        ip
        isIpPublic
        privatePort
        publicPort
        type
      }
    }
  }
}
"""

TERMINATE_POD_MUTATION = """
mutation TerminatePod($podId: String!) {
  podTerminate(input: { podId: $podId })
}
"""


class RunPodManager:
    def __init__(self, api_key: str | None = None, gpu_type: str = DEFAULT_GPU):
        self.api_key = api_key or os.environ.get("RUNPOD_API_KEY")
        if not self.api_key:
            raise RuntimeError("RUNPOD_API_KEY not set")
        self.gpu_type = gpu_type
        self.gpu_types = GPU_FALLBACKS if gpu_type == DEFAULT_GPU else [gpu_type]
        self.pod_id: str | None = None
        self._ssh_host: str | None = None
        self._ssh_port: int | None = None
        self._ssh_client: paramiko.SSHClient | None = None

    # ── Pod lifecycle ──────────────────────────────────────────────────────────

    def create_pod(self) -> str:
        last_err = None
        for gpu in self.gpu_types:
            try:
                print(f"[runpod] Trying GPU: {gpu}")
                data = _gql(
                    CREATE_POD_MUTATION,
                    {
                        "input": {
                            "gpuTypeId": gpu,
                            "imageName": DEFAULT_IMAGE,
                            "name": POD_NAME,
                            "containerDiskInGb": DISK_GB,
                            "volumeInGb": 0,
                            "ports": "22/tcp",
                            "supportPublicIp": True,
                            "startJupyter": False,
                            "startSsh": True,
                        }
                    },
                    self.api_key,
                )
                self.pod_id = data["podFindAndDeployOnDemand"]["id"]
                self.gpu_type = gpu
                print(f"[runpod] Pod created ({gpu}): {self.pod_id}")
                return self.pod_id
            except RuntimeError as e:
                if "SUPPLY_CONSTRAINT" in str(e) or "no longer any instances" in str(e):
                    print(f"[runpod] {gpu} unavailable, trying next...")
                    last_err = e
                else:
                    raise
        raise RuntimeError(f"No GPU available from fallback list. Last error: {last_err}")

    def wait_for_ssh(
        self,
        timeout: int = 300,
        poll_interval: int = 10,
        log: Callable[[str], None] = print,
    ) -> tuple[str, int]:
        """Block until pod is running and SSH port is reachable. Returns (host, port)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            data = _gql(GET_POD_QUERY, {"podId": self.pod_id}, self.api_key)
            pod = data["pod"]
            status = pod.get("desiredStatus", "")
            runtime = pod.get("runtime") or {}
            ports = runtime.get("ports") or []

            ssh_port_info = next(
                (p for p in ports if p.get("privatePort") == 22 and p.get("isIpPublic")),
                None,
            )

            if status == "RUNNING" and ssh_port_info:
                host = ssh_port_info["ip"]
                port = int(ssh_port_info["publicPort"])
                # verify TCP connectivity
                try:
                    with socket.create_connection((host, port), timeout=5):
                        pass
                    self._ssh_host = host
                    self._ssh_port = port
                    log(f"[runpod] SSH ready: {host}:{port}")
                    return host, port
                except OSError:
                    pass

            log(f"[runpod] Waiting for pod ({status})...")
            time.sleep(poll_interval)

        raise TimeoutError(f"Pod SSH not ready after {timeout}s")

    def terminate(self) -> None:
        if self.pod_id:
            if self._ssh_client:
                try:
                    self._ssh_client.close()
                except Exception:
                    pass
                self._ssh_client = None
            _gql(TERMINATE_POD_MUTATION, {"podId": self.pod_id}, self.api_key)
            print(f"[runpod] Pod {self.pod_id} terminated")
            self.pod_id = None

    # ── SSH helpers ────────────────────────────────────────────────────────────

    def _get_client(self, key_path: str | Path | None = None) -> paramiko.SSHClient:
        if self._ssh_client and self._ssh_client.get_transport() and \
                self._ssh_client.get_transport().is_active():
            return self._ssh_client

        key_path = Path(key_path) if key_path else Path.home() / ".ssh" / "id_ed25519"
        pkey = paramiko.Ed25519Key.from_private_key_file(str(key_path))

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self._ssh_host,
            port=self._ssh_port,
            username="root",
            pkey=pkey,
            timeout=30,
        )
        self._ssh_client = client
        return client

    def run(self, command: str, key_path: str | Path | None = None) -> tuple[str, str]:
        """Run a shell command on the pod. Returns (stdout, stderr)."""
        client = self._get_client(key_path)
        _, stdout, stderr = client.exec_command(command, timeout=600)
        out = stdout.read().decode()
        err = stderr.read().decode()
        rc = stdout.channel.recv_exit_status()
        if rc != 0:
            raise RuntimeError(f"Remote command failed (rc={rc}):\n{err}")
        return out, err

    def upload(self, local: Path, remote: str, key_path: str | Path | None = None) -> None:
        client = self._get_client(key_path)
        sftp = client.open_sftp()
        try:
            sftp.put(str(local), remote)
        finally:
            sftp.close()

    def download(self, remote: str, local: Path, key_path: str | Path | None = None) -> None:
        client = self._get_client(key_path)
        sftp = client.open_sftp()
        try:
            local.parent.mkdir(parents=True, exist_ok=True)
            sftp.get(remote, str(local))
        finally:
            sftp.close()

    def upload_dir(self, local_dir: Path, remote_dir: str, key_path: str | Path | None = None) -> None:
        """Recursively upload a local directory to the pod."""
        client = self._get_client(key_path)
        sftp = client.open_sftp()
        try:
            _sftp_put_dir(sftp, local_dir, remote_dir)
        finally:
            sftp.close()

    def download_dir(self, remote_dir: str, local_dir: Path, key_path: str | Path | None = None) -> None:
        """Recursively download a remote directory from the pod."""
        client = self._get_client(key_path)
        sftp = client.open_sftp()
        try:
            _sftp_get_dir(sftp, remote_dir, local_dir)
        finally:
            sftp.close()


def _sftp_put_dir(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    try:
        sftp.mkdir(remote)
    except OSError:
        pass
    for item in local.iterdir():
        r = f"{remote}/{item.name}"
        if item.is_dir():
            _sftp_put_dir(sftp, item, r)
        else:
            sftp.put(str(item), r)


def _sftp_get_dir(sftp: paramiko.SFTPClient, remote: str, local: Path) -> None:
    local.mkdir(parents=True, exist_ok=True)
    for attr in sftp.listdir_attr(remote):
        r = f"{remote}/{attr.filename}"
        l = local / attr.filename
        import stat
        if stat.S_ISDIR(attr.st_mode):
            _sftp_get_dir(sftp, r, l)
        else:
            sftp.get(r, str(l))
