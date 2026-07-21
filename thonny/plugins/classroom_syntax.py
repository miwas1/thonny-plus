"""Loader kept separate so Thonny discovers classroom syntax support automatically."""


def load_plugin() -> None:
    from thonny.plugins.classroom.syntax import install_cross_language_coloring

    install_cross_language_coloring()
