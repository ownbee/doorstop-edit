import subprocess
from datetime import datetime
from pathlib import Path

FILE_TEMPLATE = """
GIT_DESCRIBE = "{git_describe}"
GIT_COMMIT = "{commit}"
DATE = "{date}"
"""


def gen_build_info_file():
    git_describe = subprocess.check_output(["git", "describe", "--always", "--dirty"]).decode("utf-8").strip()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    date = datetime.today().isoformat()

    build_info_file = Path(__file__).parent.parent / "doorstop_edit" / "build_info.py"

    if not build_info_file.parent.is_dir():
        raise RuntimeError(f"Misplaced {build_info_file}")

    build_info_file.write_text(FILE_TEMPLATE.format(git_describe=git_describe, commit=commit, date=date))


if __name__ == "__main__":
    gen_build_info_file()
