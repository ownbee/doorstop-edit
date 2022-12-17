import argparse
import subprocess
import sys
from pathlib import Path
from typing import List

from colorama import Fore, Style, just_fix_windows_console

just_fix_windows_console()


class CheckError(RuntimeError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


def indent_text(text: str, indent: int) -> str:
    ind = " " * indent
    return "".join([(ind + line) for line in text.splitlines(keepends=True)])


def check(name: str):
    def wrapper(func):
        def decorate(*arg, **kwargs):
            print(f"{Fore.CYAN}>>> Running {name}: {Style.RESET_ALL}", end="")
            try:
                retval = func(*arg, **kwargs)
                print(f"{Fore.GREEN}PASSED.{Style.RESET_ALL}")
                return retval
            except subprocess.CalledProcessError as e:
                print(f"{Fore.RED}FAILED.{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Return code:{Fore.RED} {e.returncode}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Output:{Style.RESET_ALL}")
                print(indent_text(e.stderr.decode("utf-8"), 4), end="")
                print(indent_text(e.stdout.decode("utf-8"), 4), end="")
                print()
                command = " ".join(e.cmd)
                if len(command) > 80:
                    command = command[:80] + " ..."
                msg = f"{Fore.CYAN}Command:\n{Style.RESET_ALL}"
                msg += indent_text(command, 4)
                raise CheckError(msg) from e

        return decorate

    return wrapper


@check("black")
def run_black(files: List[Path], fix: bool) -> None:
    args = ["black"]
    if not fix:
        args += ["--check"]
    args += [str(p) for p in files]
    subprocess.check_output(args, stderr=subprocess.PIPE)


@check("autoflake")
def run_autoflake(files: List[Path], fix: bool) -> None:
    args = ["autoflake", "--remove-unused-variables", "--quiet"]
    if fix:
        args += ["--in-place"]
    else:
        args += ["--check-diff"]
    args += [str(p) for p in files]
    subprocess.check_output(args, stderr=subprocess.PIPE)


@check("isort")
def run_isort(files: List[Path], fix: bool) -> None:
    args = ["isort", "--color"]
    if not fix:
        args += ["--check-only"]
    args += [str(p) for p in files]
    subprocess.check_output(args, stderr=subprocess.PIPE)


@check("flake8")
def run_flake8(files: List[Path], _: bool) -> None:
    args = ["flake8", "--color", "always"]
    args += [str(p) for p in files]
    subprocess.check_output(args, stderr=subprocess.PIPE)


def get_git_files() -> List[Path]:
    retval = []
    output = subprocess.check_output(["git", "ls-files"]).decode("utf-8")
    for line in output.splitlines():
        p = Path(line)
        if not p.is_file():
            raise RuntimeError(f"{p.as_posix()} is not a file. Hint: Stage your changes.")
        retval.append(p)
    return retval


def get_py_files(files: List[Path]) -> List[Path]:
    return [f for f in files if f.suffix == ".py"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args()

    all_files = get_git_files()
    py_files = get_py_files(all_files)

    py_checks = [run_black, run_autoflake, run_isort, run_flake8]
    fail = False
    for check in py_checks:
        try:
            check(py_files, args.fix)
        except CheckError as e:
            print(e)
            fail = True
    if fail:
        print("\nHint: Try --fix to automatically format/fix code")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
