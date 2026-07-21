import json
import unittest

from thonny.plugins.classroom.adapters import Diagnostic
from thonny.plugins.classroom.model_worker import extract_response, make_prompt
from thonny.plugins.classroom.tutor import build_request


class ClassroomModelWorkerTests(unittest.TestCase):
    def setUp(self):
        self.diagnostic = Diagnostic(
            language="go",
            execution_phase="compile",
            error_type="undefined_name",
            line=7,
            column=2,
            raw_message="undefined: total",
            relevant_code="   6 | value := 2\n   7 | fmt.Println(total)",
        )

    def test_prompt_contains_only_normalized_tutor_request(self):
        request = build_request(self.diagnostic, "hint", "beginner", 1)
        prompt = make_prompt(request)
        self.assertIn("undefined: total", prompt)
        self.assertIn("previous_hint_count", prompt)
        self.assertNotIn("editor_contents", prompt)
        self.assertNotIn("complete_program", prompt)

    def test_structured_json_is_extracted_from_llama_output(self):
        expected = {
            "explanation": "The name is unknown.",
            "concept": "variables and names",
            "question": "Where was it created?",
            "hint": "Compare the spelling.",
        }
        output = "local model log\n" + json.dumps(expected) + "\nperformance log"
        self.assertEqual(extract_response(output), expected)

    def test_incomplete_output_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_response('{"explanation":"hello"}')


if __name__ == "__main__":
    unittest.main()
