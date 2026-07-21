"""Keep the learner workspace focused on editor, controls/output, and tutor."""

from thonny import get_workbench


def _focus_workspace(event=None) -> None:
    workbench = get_workbench()
    for view_id in tuple(workbench._view_records):
        if view_id != "ClassroomView":
            workbench.hide_view(view_id)
    workbench.show_view("ClassroomView", False)


def load_plugin() -> None:
    get_workbench().bind("WorkbenchReady", _focus_workspace, True)
