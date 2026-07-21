import importlib.util
import importlib.metadata
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
    def test_python_only_refresh_prunes_stale_language_runtimes(self):
        stage_bundle = load("stage_bundle")
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            stale_files = (
                app / "runtimes" / "node" / "node.exe",
                app / "runtimes" / "go" / "bin" / "go.exe",
                app / "licenses" / "NODE-LICENSE.txt",
                app / "tutor" / "llama-cli.exe",
            )
            for path in stale_files:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            stage_bundle.prune_removed_components(app)
            self.assertTrue(all(not path.exists() for path in stale_files))

    def test_stager_installs_discoverable_thonny_metadata(self):
        stage_bundle = load("stage_bundle")
        with tempfile.TemporaryDirectory() as directory:
            site_packages = Path(directory)
            stage_bundle.install_thonny_metadata(site_packages)
            thonny_distribution = next(
                dist
                for dist in importlib.metadata.distributions(path=[str(site_packages)])
                if dist.metadata["Name"] == "thonny"
            )
            discovered_version = thonny_distribution.version
        self.assertEqual(
            discovered_version,
            (Path(__file__).parent / "thonny" / "VERSION")
            .read_text(encoding="ascii")
            .strip(),
        )

    def test_source_checkout_does_not_show_package_metadata_error(self):
        source = (Path(__file__).parent / "thonny" / "workbench.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("except PackageNotFoundError:", source)
        self.assertIn("Skipping package version alignment check", source)

    def test_empty_bundle_reports_runtime_model_and_notices(self):
        verify_bundle = load("verify_bundle")
        import sys

        sys.modules["verify_bundle"] = verify_bundle
        verify_release = load("verify_release")
        with tempfile.TemporaryDirectory() as directory:
            errors = verify_release.verify_release(Path(directory), {})
        joined = "\n".join(errors)
        self.assertNotIn("runtimes/node/node.exe", joined)
        self.assertNotIn("runtimes/go/bin/go.exe", joined)
        self.assertIn("tutor/llama-server.exe", joined)
        self.assertIn("qwen-coder-1.5b-q4_k_m.gguf", joined)
        self.assertIn("QWEN-LICENSE.txt", joined)
        self.assertIn("basedpyright/langserver.py", joined)
        self.assertIn("ruff/__main__.py", joined)
        self.assertIn("package metadata", joined)

    def test_release_workflow_is_manual_oidc_and_sha_pinned(self):
        workflow = (
            Path(__file__).parent
            / ".github"
            / "workflows"
            / "release-windows-classroom.yml"
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

        manifest = json.loads(
            (MODULE_DIR / "artifacts.json").read_text(encoding="utf-8")
        )
        model = manifest["qwen"]
        self.assertNotIn("node", manifest)
        self.assertNotIn("go", manifest)
        self.assertRegex(model["revision"], r"^[0-9a-f]{40}$")
        self.assertIn(model["revision"], model["url"])
        self.assertRegex(model["sha256"], r"^[0-9a-f]{64}$")

    def test_stager_enables_private_site_packages_and_never_tracks_model(self):
        stager = (MODULE_DIR / "stage_bundle.py").read_text(encoding="utf-8")
        ignore = (Path(__file__).parent / ".gitignore").read_text(encoding="utf-8")
        self.assertIn('lines.append("Lib/site-packages")', stager)
        self.assertIn('lines.append("import site")', stager)
        self.assertIn("*.gguf", ignore)
        self.assertIn('downloads["qwen"]', stager)
        self.assertIn("shutil.rmtree(installed_package)", stager)
        self.assertIn("def prune_removed_components", stager)
        self.assertIn('app / "runtimes" / "node"', stager)
        self.assertIn("write_bundle_metadata(app, manifest)", stager)

    def test_windows_server_entrypoint_builds_and_smoke_tests_qwen_installer(self):
        root = Path(__file__).parent
        script = (root / "build-windows-classroom.ps1").read_text(encoding="utf-8")
        ignore = (root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn('"stage_bundle.py"', script)
        self.assertIn('"smoke_bundle.py"', script)
        self.assertIn("--with-model", script)
        self.assertIn('"build_installer.ps1"', script)
        self.assertIn("resumeStagedBundle", script)
        self.assertIn("Resuming the verified staged bundle", script)
        self.assertIn("--refresh-source", script)
        self.assertIn("version[1] -ne 13", script)
        self.assertNotIn("version[1] -ne 14", script)
        self.assertIn("/.classroom-build/", ignore)
        self.assertIn("/.classroom-cache/", ignore)
        self.assertIn("*.gguf", ignore)

        workflow = (
            root / ".github" / "workflows" / "release-windows-classroom.yml"
        ).read_text(encoding="utf-8-sig")
        self.assertIn('python-version: "3.13"', workflow)

        stager = (MODULE_DIR / "stage_bundle.py").read_text(encoding="utf-8")
        self.assertIn('embedded_python = app / "thonny" / "python.exe"', stager)
        self.assertIn("str(embedded_python)", stager)
        self.assertIn("if args.refresh_source:", stager)
        self.assertIn("if not args.skip_dependencies:", stager)
        self.assertNotIn('"runtimes/node/node.exe"', stager)
        self.assertNotIn('"runtimes/go/bin/go.exe"', stager)

        smoke = (MODULE_DIR / "smoke_bundle.py").read_text(encoding="utf-8")
        self.assertIn("client.start_count != 1", smoke)
        self.assertIn("warm_seconds", smoke)
        self.assertIn("llama-server.exe", smoke)
        self.assertIn("def exercise_language_services", smoke)


if __name__ == "__main__":
    unittest.main()
