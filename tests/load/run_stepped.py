"""Find the round's capacity: run the k6 journey at rising user counts until a budget fails.

Each step starts from a fresh stack, so earlier steps' accounts and tasks never slow a later one.
The capacity figure is the last step whose budgets all held. Results go to tests/load/results/<UTC>-<sha>/.

Usage, from the repo root: python3 tests/load/run_stepped.py [--steps 200,400,600,800,1000] [--hold 2m]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "tests" / "load" / "results"
log = logging.getLogger("run_stepped")


def output(*command: str) -> str:
    """Run a command and return its trimmed standard output."""
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def machine() -> dict[str, str]:
    """Describe the Mac and Docker's share of it; nothing that identifies the machine, such as a serial number."""
    model, cpu, cores, memory = output(
        "sysctl", "-n", "hw.model", "machdep.cpu.brand_string", "hw.ncpu", "hw.memsize"
    ).splitlines()
    docker_cpus, docker_memory = output("docker", "info", "--format", "{{.NCPU}} {{.MemTotal}}").split()
    return {
        "model": model,
        "cpu": cpu,
        "cores": cores,
        "memory_gib": f"{int(memory) / 2**30:.0f}",
        "docker_cpus": docker_cpus,
        "docker_memory_gib": f"{int(docker_memory) / 2**30:.1f}",
    }


def fresh_stack(sha: str) -> None:
    """Remove the stack and its database volume, then build and start it again."""
    subprocess.run(["docker", "compose", "down", "-v"], cwd=ROOT, check=True)
    subprocess.run(
        ["docker", "compose", "up", "--build", "--wait"], cwd=ROOT, check=True, env={**os.environ, "GIT_SHA": sha}
    )


def run_step(vus: int, hold: str, results_dir: str, sha: str) -> bool:
    """Run the journey at `vus` users; True when k6 exits 0, which means every budget held."""
    settings = [f"VUS={vus}", f"HOLD={hold}", f"RESULTS_DIR=/results/{results_dir}"]
    command = [
        *["docker", "compose", "--profile", "load", "run", "--rm"],
        *(part for setting in settings for part in ("-e", setting)),
        *["k6", "run", "/scripts/journey.js"],
    ]
    # The same GIT_SHA as the stack, or compose would resolve other image tags and recreate the stack under test.
    return subprocess.run(command, cwd=ROOT, env={**os.environ, "GIT_SHA": sha}).returncode == 0


def main() -> int:
    """Run each step in order, stop at the first that misses a budget, and record the capacity."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--steps", default="200,400,600,800,1000", help="comma-separated user counts, in order")
    parser.add_argument("--hold", default="2m", help="how long each step holds its full user count")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="== %(message)s")
    steps = [int(step) for step in args.steps.split(",")]

    sha = output("git", "rev-parse", "--short", "HEAD")
    run_name = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{sha}"
    run_dir = RESULTS / run_name
    run_dir.mkdir(parents=True)
    (run_dir / "machine.json").write_text(json.dumps(machine(), indent=2) + "\n")

    outcomes: list[dict[str, object]] = []
    for vus in steps:
        log.info("step: %s users, hold %s", vus, args.hold)
        fresh_stack(sha)
        passed = run_step(vus, args.hold, run_name, sha)
        outcomes.append({"vus": vus, "passed": passed})
        if not passed:
            break

    passed_steps = [outcome["vus"] for outcome in outcomes if outcome["passed"]]
    capacity = {
        "capacity_vus": passed_steps[-1] if passed_steps else None,
        "hold": args.hold,
        "sha": sha,
        "steps": outcomes,
    }
    (run_dir / "capacity.json").write_text(json.dumps(capacity, indent=2) + "\n")
    log.info("capacity: %s users; results in %s", capacity["capacity_vus"], run_dir.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
