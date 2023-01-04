from unittest import TestCase, mock

from PySide6.QtWidgets import QApplication

from doorstop_edit.main import setup as main_setup

app = QApplication()


class TestMain(TestCase):
    def test_start_no_exceptions(self):
        editor = main_setup(app, ["app"])
        self.assertIsNotNone(editor)

    def test_arg_version(self):
        with mock.patch("builtins.print") as mocked_print:
            editor = main_setup(app, ["app", "--version"])
            self.assertIsNone(editor)

        self.assertIn("Version:", mocked_print.call_args_list[0].args[0])
        self.assertIn("Commit:", mocked_print.call_args_list[0].args[0])
