from contextlib import contextmanager
from typing import Any, Iterator, Optional
from unittest import mock

from PySide6.QtWidgets import QApplication

from doorstop_edit.application import DoorstopEdit
from doorstop_edit.main import setup as main_setup

# Using pytest-qt fixtures


@contextmanager
def setup_ctx(*args: Any, **kwds: Any) -> Iterator[Optional[DoorstopEdit]]:
    app = main_setup(*args, **kwds)
    yield app
    if app is not None:
        # Needs to called to cleanup threads etc. Work-around since QApplication wont process quit
        # calls if not QApplication.exec() is called (which we dont wanna call in tests).
        app.quit()


def test_start_no_exceptions(qapp: QApplication) -> None:
    with setup_ctx(qapp, ["name"]) as app:
        assert app is not None


def test_arg_version(qapp: QApplication) -> None:
    with mock.patch("builtins.print") as mocked_print:
        with setup_ctx(qapp, ["name", "--version"]) as app:
            assert app is None

    print_msg = mocked_print.call_args_list[0].args[0]
    assert "Version:" in print_msg
    assert "Commit:" in print_msg
