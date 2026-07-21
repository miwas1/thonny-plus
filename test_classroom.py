import sys
import tempfile
import unittest
from pathlib import Path

from thonny.plugins.classroom.adapters import (
    GoAdapter,
    JavaScriptAdapter,
    PythonAdapter,
)
from thonny.plugins.classroom.runtime import (
    SAMPLES,
    bundled_adapters,
    language_for_path,
)
from thonny.plugins.classroom.tutor import (
    ACTIONS,
    SYSTEM_POLICY,
    build_request,
    context_from_run,
    deterministic_response,
    enforce_response_word_limits,
    render_response,
    select_tutor_action,
)


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
        self.assertEqual(
            (diagnostic.error_type, diagnostic.line), ("undefined_name", 7)
        )
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
        env = GoAdapter(
            "/app/go/bin/go", "/app/go", tempfile.mkdtemp()
        ).build_environment(Path("main.go"))
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

    def test_every_mvp_tutor_activity_has_a_bounded_fallback(self):
        context = context_from_run(
            language="javascript",
            source="let total = 0;\nfor (let i = 0; i < 3; i++) total += i;\nconsole.log(total);",
            actual_output="3",
            expected_output="6",
            test_results="FAILED test_total: expected 6, received 3",
            session_progress="completed 2 successful run(s)",
        )
        for action in ACTIONS:
            response = deterministic_response(context, action)
            rendered = render_response(response, action)
            self.assertLessEqual(len(rendered.split()), 100, action)
            self.assertNotIn("```", rendered, action)

    def test_model_policy_explicitly_forbids_solution_generation(self):
        self.assertIn("Never write code for the learner", SYSTEM_POLICY)
        self.assertIn("untrusted data", SYSTEM_POLICY)
        self.assertIn("below 100 words", SYSTEM_POLICY)

    def test_model_response_fields_are_trimmed_to_the_classroom_budget(self):
        long_text = " ".join(f"word{index}" for index in range(100))
        limited = enforce_response_word_limits(
            {
                "explanation": long_text,
                "concept": long_text,
                "question": long_text,
                "hint": long_text,
            }
        )
        self.assertLessEqual(sum(len(value.split()) for value in limited.values()), 80)
        self.assertTrue(all(value.endswith("…") for value in limited.values()))

    def test_source_context_is_bounded_and_request_supports_no_error(self):
        source = "\n".join(f"value_{index} = {index}" for index in range(200))
        context = context_from_run("python", source)
        self.assertIn("remaining lines omitted", context.source_excerpt)
        self.assertNotIn("value_199", context.source_excerpt)
        request = build_request(context, "quiz")
        self.assertIsNone(request["context"]["diagnostic"])
        self.assertEqual(request["action"], "quiz")

    def test_tutor_strategy_is_selected_from_context(self):
        diagnostic = PythonAdapter().parse_diagnostics(
            "File \"x.py\", line 1\nNameError: name 'x' is not defined", "print(x)"
        )
        assert diagnostic
        error_context = context_from_run("python", "print(x)", diagnostic=diagnostic)
        self.assertEqual(select_tutor_action(error_context, "run"), "explain")
        self.assertEqual(
            select_tutor_action(error_context, "run", diagnostic_runs=2),
            "misconception",
        )
        self.assertEqual(
            select_tutor_action(error_context, "run", diagnostic_runs=4),
            "next_step",
        )
        self.assertEqual(
            select_tutor_action(error_context, "hint", hint_count=2),
            "rubber_duck",
        )

        successful = context_from_run("python", "print(3)", actual_output="3")
        self.assertEqual(select_tutor_action(successful, "help"), "trace")
        self.assertEqual(select_tutor_action(successful, "quiz"), "quiz")

        tests = context_from_run(
            "python",
            "print(3)",
            test_results="FAILED test_total: expected 6, received 3",
        )
        self.assertEqual(select_tutor_action(tests, "run"), "test_results")

    def test_coach_ui_does_not_expose_internal_activity_menu(self):
        ui_source = (
            Path(__file__).parent / "thonny" / "plugins" / "classroom" / "ui.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("More learning activities", ui_source)
        self.assertNotIn("tutor_activity", ui_source)
        self.assertIn("Help me understand", ui_source)
        self.assertIn("One hint", ui_source)

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
            result = PythonAdapter(sys.executable).run_file(
                path, input_text="hello classroom\n"
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "hello classroom\n")


if __name__ == "__main__":
    unittest.main()
