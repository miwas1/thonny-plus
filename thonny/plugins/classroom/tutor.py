from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from typing import Literal

from thonny.plugins.classroom.adapters import Diagnostic

SYSTEM_POLICY = """You are a patient programming tutor for first-time learners.

Never write the complete solution.
Never replace the learner's program.
Explain only the current error or requested concept.
Give one hint at a time.
Use simple language.
Ask the learner to predict or try something before revealing more.
Keep the entire response below 100 words.
Return JSON with explanation, concept, question, and hint fields only.
"""

TutorAction = Literal["explain", "hint", "concept", "question"]


@dataclass(frozen=True)
class TutorResponse:
    explanation: str
    concept: str
    question: str
    hint: str


CONCEPTS = {
    "undefined_name": "variables and names",
    "syntax_error": "program structure and punctuation",
    "indentation_error": "indentation and code blocks",
    "type_error": "values and data types",
    "division_by_zero": "division and valid numeric inputs",
}


def deterministic_response(
    diagnostic: Diagnostic, action: TutorAction = "explain"
) -> TutorResponse:
    concept = CONCEPTS.get(diagnostic.error_type, "reading error messages")
    where = f"line {diagnostic.line}" if diagnostic.line else "while the program was running"
    name = diagnostic.language.title()
    explanations = {
        "undefined_name": f"{name} could not find a name the program tried to use.",
        "syntax_error": f"{name} could not understand the program's structure.",
        "indentation_error": "Python found a code block whose indentation does not line up.",
        "type_error": "An operation received a kind of value it cannot use.",
        "division_by_zero": "The program tried to divide a number by zero.",
    }
    explanation = explanations.get(diagnostic.error_type, f"{name} stopped with an error.")
    hints = {
        "undefined_name": "Check where the name is first created, then compare its spelling.",
        "syntax_error": "Inspect the punctuation just before the marked location.",
        "indentation_error": "Compare the leading spaces with the lines in the same block.",
        "type_error": "Check the type of each value used by the marked operation.",
        "division_by_zero": "Find the divisor and consider when it can become zero.",
    }
    hint = hints.get(
        diagnostic.error_type, "Read the marked line and the line immediately before it."
    )
    question = f"What do you predict will change if you try that check at {where}?"
    return TutorResponse(
        explanation=f"What happened: {explanation} Where: {where}.",
        concept=f"Concept: {concept}.",
        question=question,
        hint=f"Next action: {hint}",
    )


def build_request(
    diagnostic: Diagnostic, action: TutorAction, lesson_level: str, previous_hint_count: int
) -> dict[str, object]:
    return {
        "policy": SYSTEM_POLICY,
        "action": action,
        "lesson_level": lesson_level,
        "previous_hint_count": previous_hint_count,
        "diagnostic": asdict(diagnostic),
    }


class TutorWorkerClient:
    """Line-delimited JSON client for an isolated local llama.cpp worker."""

    def __init__(self, command: list[str]) -> None:
        self.command = command

    def ask(
        self,
        diagnostic: Diagnostic,
        action: TutorAction,
        lesson_level: str = "beginner",
        previous_hint_count: int = 0,
        timeout: float = 30.0,
    ) -> TutorResponse:
        payload = build_request(diagnostic, action, lesson_level, previous_hint_count)
        completed = subprocess.run(
            self.command,
            input=json.dumps(payload) + "\n",
            text=True,
            capture_output=True,
            timeout=timeout,
            check=True,
        )
        data = json.loads(completed.stdout.splitlines()[-1])
        response = TutorResponse(**{key: str(data[key]) for key in TutorResponse.__annotations__})
        if len(" ".join(asdict(response).values()).split()) > 100:
            raise ValueError("Tutor response exceeded the 100-word classroom limit")
        return response


def render_response(response: TutorResponse, action: TutorAction) -> str:
    if action == "hint":
        return f"{response.explanation}\n\n{response.concept}\n\n{response.hint}"
    if action == "concept":
        return f"{response.explanation}\n\n{response.concept}\n\n{response.question}"
    if action == "question":
        return f"{response.explanation}\n\n{response.question}\n\n{response.hint}"
    return f"{response.explanation}\n\n{response.concept}\n\n{response.hint}"
