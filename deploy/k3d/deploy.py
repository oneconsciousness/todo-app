#!/usr/bin/env python3
"""Deploy the app to a local k3d cluster: `python3 deploy/k3d/deploy.py up`, then open https://localhost:8443.

`up` creates the cluster if it is missing, builds and imports the images for the current commit, creates the
secrets if they are missing, then applies Postgres, the migration Job and the app, each after the one before is
ready. `build`, `render` and `secrets` run one of those steps alone; `down` deletes the cluster and its data.
Every command is printed before it runs. Secret values reach kubectl on stdin and are never printed or kept.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLUSTER = "todo"
NAMESPACE = "todo"
CLUSTER_CONFIG = "deploy/k3d/cluster.yaml"
PARTS = ("platform", "migrate", "app")
# Each image and the folder it is built from, the same build compose runs.
IMAGES = {"todo-api": "backend", "todo-web": "frontend"}
SHORT_SHA = re.compile(r"[0-9a-f]{7,40}")
# The names a browser or a test on the Mac uses for the cluster's front door.
CERT_NAMES = ("localhost", "127.0.0.1", "::1")
TOOLS = ("docker", "k3d", "kubectl", "mkcert")
URL = "https://localhost:8443"

log = logging.getLogger("deploy")


def release_files(sha: str) -> dict[str, str]:
    """Return the kustomization for each part of a release, keyed by its path under `deploy/.release/<sha>/`.

    Each part builds on its k3d overlay and pins both images to the commit. The migration Job's name also
    carries the commit, so each release runs it once and a repeat deploy of the same commit changes nothing.
    """
    if not SHORT_SHA.fullmatch(sha):
        raise ValueError(f"not a short lowercase git sha: {sha!r}")
    images = "".join(f"  - name: {name}\n    newTag: {sha}\n" for name in IMAGES)

    def kustomization(part: str) -> str:
        suffix = f"nameSuffix: -{sha}\n" if part == "migrate" else ""
        return (
            "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\n"
            f"resources:\n  - ../../../overlays/k3d/{part}\n{suffix}images:\n{images}"
        )

    return {f"{part}/kustomization.yaml": kustomization(part) for part in PARTS}


def rollout_steps(sha: str) -> list[list[str]]:
    """Return the kubectl commands that roll out a written release, each waiting for the one before."""
    release = f"deploy/.release/{sha}"
    namespace = ["-n", NAMESPACE]
    return [
        ["kubectl", "apply", "-k", f"{release}/platform"],
        ["kubectl", "rollout", "status", "statefulset/db", *namespace, "--timeout=180s"],
        ["kubectl", "apply", "-k", f"{release}/migrate"],
        ["kubectl", "wait", "--for=condition=complete", f"job/migrate-{sha}", *namespace, "--timeout=180s"],
        ["kubectl", "apply", "-k", f"{release}/app"],
        ["kubectl", "rollout", "status", "deployment/api", *namespace, "--timeout=300s"],
        ["kubectl", "rollout", "status", "deployment/web", *namespace, "--timeout=180s"],
    ]


def create_secret(name: str, data: dict[str, str], kind: str = "Opaque") -> tuple[list[str], str]:
    """Return the command that creates a Secret and the manifest to send on its stdin, so no value is an argument."""
    manifest = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": name, "namespace": NAMESPACE},
        "type": kind,
        "stringData": data,
    }
    return ["kubectl", "create", "-f", "-"], json.dumps(manifest)


def run(command: list[str], stdin: str | None = None) -> None:
    """Print the command, run it from the repo root, and stop the deploy if it fails."""
    log.info("+ %s", " ".join(command))
    subprocess.run(command, cwd=REPO, input=stdin, text=True, check=True)


def succeeds(command: list[str]) -> bool:
    """Run a read-only check quietly and say whether it succeeded."""
    return subprocess.run(command, cwd=REPO, capture_output=True).returncode == 0


def current_sha() -> str:
    """Return the short sha of the checked-out commit, the tag compose gives its images too."""
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


def require_tools() -> None:
    """Stop with the install command when a tool the deploy needs is missing."""
    missing = [tool for tool in TOOLS if shutil.which(tool) is None]
    if missing:
        sys.exit(f"missing {', '.join(missing)}: brew install {' '.join(missing)} (see the README)")


def ensure_cluster() -> None:
    """Create the three-node cluster unless it already exists."""
    if not succeeds(["k3d", "cluster", "get", CLUSTER]):
        run(["k3d", "cluster", "create", "--config", CLUSTER_CONFIG])


def build(sha: str) -> None:
    """Build both images for the commit and copy them onto every node, so no pod pulls from a registry."""
    tags = [f"{name}:{sha}" for name in IMAGES]
    for tag, folder in zip(tags, IMAGES.values()):
        run(["docker", "build", "-t", tag, folder])
    run(["k3d", "image", "import", *tags, "--cluster", CLUSTER])


def write_release(sha: str) -> Path:
    """Write the release's kustomizations under `deploy/.release/<sha>/` and return that folder."""
    folder = REPO / "deploy" / ".release" / sha
    for path, text in release_files(sha).items():
        (folder / path).parent.mkdir(parents=True, exist_ok=True)
        (folder / path).write_text(text)
    return folder


def certificate() -> dict[str, str]:
    """Make a certificate for the cluster's names, signed by mkcert's local authority, and return it as Secret data."""
    with tempfile.TemporaryDirectory() as folder:
        cert, key = Path(folder) / "tls.crt", Path(folder) / "tls.key"
        run(["mkcert", "-cert-file", str(cert), "-key-file", str(key), *CERT_NAMES])
        return {"tls.crt": cert.read_text(), "tls.key": key.read_text()}


def ensure_secrets() -> None:
    """Create the namespace and each Secret that does not exist yet; existing ones, including your own, are kept."""
    if not succeeds(["kubectl", "get", "namespace", NAMESPACE]):
        # "--save-config" lets the later apply of the same namespace take it over without a warning.
        run(["kubectl", "create", "namespace", NAMESPACE, "--save-config"])
    # Hex keeps the password safe inside DATABASE_URL.
    wanted = {
        "todo-db": lambda: ({"password": secrets.token_hex(24)}, "Opaque"),
        "todo-api": lambda: ({"jwt-secret": secrets.token_hex(32)}, "Opaque"),
        "todo-tls": lambda: (certificate(), "kubernetes.io/tls"),
    }
    for name, make in wanted.items():
        # "-o name" prints only the Secret's name, never its data.
        if succeeds(["kubectl", "get", "secret", name, "-n", NAMESPACE, "-o", "name"]):
            continue
        data, kind = make()
        command, payload = create_secret(name, data, kind)
        run(command, stdin=payload)


def up(sha: str) -> None:
    """Run every step, from the cluster to a rolled-out app."""
    require_tools()
    ensure_cluster()
    build(sha)
    ensure_secrets()
    write_release(sha)
    for step in rollout_steps(sha):
        run(step)
    log.info("todo-app %s is running at %s", sha, URL)


def main() -> None:
    """Parse the subcommand and run it."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("up", "build", "render", "secrets", "down"))
    parser.add_argument("--sha", help="the commit to deploy (default: the checked-out one)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sha = args.sha or current_sha()
    actions = {
        "up": lambda: up(sha),
        "build": lambda: build(sha),
        "render": lambda: log.info("wrote %s", write_release(sha)),
        "secrets": ensure_secrets,
        "down": lambda: run(["k3d", "cluster", "delete", CLUSTER]),
    }
    try:
        actions[args.command]()
    except subprocess.CalledProcessError as error:
        sys.exit(f"stopped: {' '.join(error.cmd)} exited with {error.returncode}")


if __name__ == "__main__":
    main()
