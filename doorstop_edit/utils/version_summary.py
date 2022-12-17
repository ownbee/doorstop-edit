import platform
import sys

import doorstop
import PySide6

import doorstop_edit
from doorstop_edit import build_info


def create_version_summary() -> str:
    return f"""\
Version: {doorstop_edit.__version__}
VCS: {build_info.GIT_DESCRIBE}
Commit: {build_info.GIT_COMMIT}
Date: {build_info.DATE}
Doorstop: {doorstop.__version__}
PySide6: {PySide6.__version__}
Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}
OS: {platform.platform()}"""
