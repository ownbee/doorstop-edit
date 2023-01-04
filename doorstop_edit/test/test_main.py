from contextlib import contextmanager
from unittest import TestCase, mock

from PySide6.QtWidgets import QApplication

from doorstop_edit.main import setup as main_setup

q_app = QApplication()


@contextmanager
def setup_ctx(*args, **kwds):
    app = main_setup(*args, **kwds)
    yield app
    if app is not None:
        # Needs to called to cleanup threads etc. Work-around since QApplication wont process quit
        # calls if not QApplication.exec() is called (which we dont wanna call in tests).
        app.quit()


class TestMain(TestCase):
    def test_start_no_exceptions(self):
        with setup_ctx(q_app, ["name"]) as app:
            self.assertIsNotNone(app)

    def test_arg_version(self):
        with mock.patch("builtins.print") as mocked_print:
            with setup_ctx(q_app, ["name", "--version"]) as app:
                self.assertIsNone(app)

        self.assertIn("Version:", mocked_print.call_args_list[0].args[0])
        self.assertIn("Commit:", mocked_print.call_args_list[0].args[0])
