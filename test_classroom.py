import sys
import tempfile
import unittest
from pathlib import Path

from thonny.plugins.classroom.adapters import GoAdapter, JavaScriptAdapter, PythonAdapter
from thonny.plugins.classroom.runtime import SAMPLES, bundled_adapters, language_for_path
from thonny.plugins.classroom.tutor import build_request, deterministic_response, render_response


class ClassroomTests(unittest.TestCase):
    def test_language_selection_and_samples(self):
        self.assertEqual(language_for_path("hello.py"), "python")
        self.assertEqual(language_for_path("hello.js"), "javascript")
        self.assertEqual(language_for_path("hello.go"), "go")
        self.assertIn("Hello!", SAMPLES["go"])

    def test_bundled_python_reuses_complete_thonny_distribution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            python_exe = root / "thonny" / "python.exe"
            python_exe.parent.mkdir()
            python_exe.touch()
            adapters = bundled_adapters(root / "user", root)
            self.assertEqual(adapters["python"].executable, python_exe)

    def test_python_diagnostic_is_normalized_and_context_is_bounded(self):
        source = "\n".join(f"line_{i} = {i}" for i in range(1, 14))
        raw = "Traceback (most recent call last):\n  File \"x.py\", line 7, in <module>\nNameError: name 'total' is not defined\n"
        diagnostic = PythonAdapter().parse_diagnostics(raw, source)
        assert diagnostic
        self.assertEqual((diagnostic.error_type, diagnostic.line), ("undefined_name", 7))
        self.assertEqual(len(diagnostic.relevant_code.splitlines()), 9)
        self.assertNotIn("line_1 =", diagnostic.relevant_code)

    def test_javascript_and_go_diagnostics(self):
        js = JavaScriptAdapter("node").parse_diagnostics(
            "/work/a.js:3\nReferenceError: total is not defined", "a\nb\ntotal"
        )
        assert js
        self.assertEqual((js.error_type, js.line), ("undefined_name", 3))
        go = GoAdapter("go", "/go", "/tmp/cache").parse_diagnostics(
            "./main.go:7:2: undefined: total", "\n" * 6 + "total"
        )
        assert go
        self.assertEqual((go.execution_phase, go.column), ("compile", 2))

    def test_go_environment_disables_network_modules(self):
        env = GoAdapter("/app/go/bin/go", "/app/go", tempfile.mkdtemp()).build_environment(
            Path("main.go")
        )
        self.assertEqual((env["GOPROXY"], env["GO111MODULE"]), ("off", "off"))

    def test_tutor_payload_is_restricted_and_short(self):
        diagnostic = PythonAdapter().parse_diagnostics(
            "File \"x.py\", line 1\nNameError: name 'x' is not defined", "print(x)"
        )
        assert diagnostic
        request = build_request(diagnostic, "hint", "beginner", 2)
        self.assertEqual(request["previous_hint_count"], 2)
        rendered = render_response(deterministic_response(diagnostic, "hint"), "hint")
        self.assertLessEqual(len(rendered.split()), 100)
        self.assertIn("Next action", rendered)

    def test_timeout_stops_process(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "loop.py"
            path.write_text("while True:\n    pass\n", encoding="utf-8")
            result = PythonAdapter(sys.executable, timeout=0.1).run_file(path)
            self.assertTrue(result.timed_out)
            self.assertNotEqual(result.returncode, 0)

    def test_standard_input_is_delivered_to_program(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.py"
            path.write_text("print(input())\n", encoding="utf-8")
            result = PythonAdapter(sys.executable).run_file(path, input_text="hello classroom\n")
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "hello classroom\n")


if __name__ == "__main__":
    unittest.main()
