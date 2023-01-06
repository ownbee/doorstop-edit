import subprocess
from datetime import datetime
from pathlib import Path

FILE_TEMPLATE = """
GIT_DESCRIBE = "{git_describe}"
GIT_COMMIT = "{commit}"
DATE = "{date}"
"""


def gen_build_info_file() -> None:
    print("Generating build info file...")
    git_describe = subprocess.check_output(["git", "describe", "--always", "--dirty"]).decode("utf-8").strip()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    date = datetime.today().isoformat()

    root = Path(__file__).parent.parent
    build_info_file = root / "doorstop_edit" / "build_info.py"

    if not build_info_file.parent.is_dir():
        raise RuntimeError(f"Misplaced {build_info_file}")

    build_info_file.write_text(FILE_TEMPLATE.format(git_describe=git_describe, commit=commit, date=date))
    print(f"  -> {build_info_file.relative_to(root)}")


if __name__ == "__main__":
    gen_build_info_file()
