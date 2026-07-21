"""Apply the complete classroom response contract to local tutor requests."""

from thonny.plugins.classroom import tutor

RESPONSE_CONTRACT = """
Every response must state what happened, where it happened, one concept involved,
and exactly one next action. Keep the combined response below 100 words.
Do not reveal a second hint in the same response.
"""


def load_plugin() -> None:
    if RESPONSE_CONTRACT.strip() not in tutor.SYSTEM_POLICY:
        tutor.SYSTEM_POLICY += RESPONSE_CONTRACT
