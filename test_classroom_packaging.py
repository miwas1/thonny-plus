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


if __name__ == "__main__":
    unittest.main()
