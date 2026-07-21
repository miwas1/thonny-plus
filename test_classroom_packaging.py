import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).parent / "packaging" / "windows" / "classroom"


def load(name):
    spec = importlib.util.spec_from_file_location(name, MODULE_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PackagingGateTests(unittest.TestCase):
    def test_empty_bundle_reports_runtime_model_and_notices(self):
        verify_bundle = load("verify_bundle")
        import sys

        sys.modules["verify_bundle"] = verify_bundle
        verify_release = load("verify_release")
        with tempfile.TemporaryDirectory() as directory:
            errors = verify_release.verify_release(Path(directory), {})
        joined = "\n".join(errors)
        self.assertIn("runtimes/node/node.exe", joined)
        self.assertIn("tutor/llama-cli.exe", joined)
        self.assertIn("qwen-coder-1.5b-q4_k_m.gguf", joined)
        self.assertIn("QWEN-LICENSE.txt", joined)

    def test_release_workflow_is_manual_oidc_and_sha_pinned(self):
        workflow = (
            Path(__file__).parent / ".github" / "workflows" / "release-windows-classroom.yml"
        ).read_text(encoding="utf-8-sig")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertNotIn("\n  pull_request:", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("aws-actions/configure-aws-credentials@", workflow)
        self.assertNotIn("AWS_ACCESS_KEY_ID", workflow)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", workflow)
        for line in workflow.splitlines():
            if "uses:" in line:
                revision = line.split("@", 1)[1].split()[0]
                self.assertRegex(revision, r"^[0-9a-f]{40}$")

    def test_model_artifact_is_revision_and_checksum_pinned(self):
        import json

        manifest = json.loads((MODULE_DIR / "artifacts.json").read_text(encoding="utf-8"))
        model = manifest["qwen"]
        self.assertRegex(model["revision"], r"^[0-9a-f]{40}$")
        self.assertIn(model["revision"], model["url"])
        self.assertRegex(model["sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
