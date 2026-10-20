"""Check the pure parts of deploy.py: the release it writes, the order of its steps, and how it passes secrets."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "deploy.py"
spec = importlib.util.spec_from_file_location("deploy", SCRIPT)
assert spec is not None and spec.loader is not None
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)

SHA = "abc1234"


class ReleaseTest(unittest.TestCase):
    def test_every_part_pins_both_images_to_the_commit(self) -> None:
        for text in deploy.release_files(SHA).values():
            self.assertIn("name: todo-api\n    newTag: abc1234", text)
            self.assertIn("name: todo-web\n    newTag: abc1234", text)

    def test_only_the_migration_job_name_carries_the_commit(self) -> None:
        files = deploy.release_files(SHA)

        self.assertIn("nameSuffix: -abc1234", files["migrate/kustomization.yaml"])
        self.assertNotIn("nameSuffix", files["platform/kustomization.yaml"] + files["app/kustomization.yaml"])

    def test_each_part_builds_on_its_k3d_overlay(self) -> None:
        release = deploy.REPO / "deploy" / ".release" / SHA
        for path, text in deploy.release_files(SHA).items():
            [resource] = [line.strip()[2:] for line in text.splitlines() if line.startswith("  - ../")]
            part = Path(path).parent.name
            self.assertEqual((release / part / resource).resolve(), deploy.REPO / "deploy" / "overlays" / "k3d" / part)

    def test_a_commit_that_is_not_a_short_hex_sha_is_refused(self) -> None:
        for bad in ("", "main", "abc1234\nnameSuffix: x", "ABC1234"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                deploy.release_files(bad)


class StepsTest(unittest.TestCase):
    def test_the_app_rolls_out_only_after_the_migration_completes(self) -> None:
        steps = [" ".join(step) for step in deploy.rollout_steps(SHA)]

        def index(fragment: str) -> int:
            return next(n for n, step in enumerate(steps) if fragment in step)

        self.assertLess(index("rollout status statefulset/db"), index("apply -k deploy/.release/abc1234/migrate"))
        self.assertLess(index("apply -k deploy/.release/abc1234/migrate"), index("wait --for=condition=complete"))
        self.assertLess(index("wait --for=condition=complete"), index("apply -k deploy/.release/abc1234/app"))
        self.assertEqual(index("job/migrate-abc1234"), index("wait --for=condition=complete"))


class SecretTest(unittest.TestCase):
    def test_secret_values_go_on_stdin_never_in_the_command(self) -> None:
        command, payload = deploy.create_secret("todo-db", {"password": "s3cret-value"})

        self.assertNotIn("s3cret-value", " ".join(command))
        self.assertEqual(command[-2:], ["-f", "-"])
        self.assertEqual(json.loads(payload)["stringData"], {"password": "s3cret-value"})
        self.assertEqual(json.loads(payload)["metadata"], {"name": "todo-db", "namespace": "todo"})

    def test_a_tls_secret_has_the_tls_type(self) -> None:
        _, payload = deploy.create_secret("todo-tls", {"tls.crt": "C", "tls.key": "K"}, kind="kubernetes.io/tls")

        self.assertEqual(json.loads(payload)["type"], "kubernetes.io/tls")


if __name__ == "__main__":
    unittest.main()
