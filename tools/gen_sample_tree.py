import argparse
import shutil
from pathlib import Path
from typing import Generator, List, Tuple

import requests

DOT_DOORSTOP_TEMPLATE = """\
settings:
  digits: 3
  prefix: {prefix}
  sep: '-'
  {parent}
attributes:
  publish:
    - custom1
    - custom2
"""

MD_LIST = """\
  * Occaecat enim aute deserunt.
  * Eu veniam eiusmod.
  * **Culpa** anim aute.\
"""

MD_TABLE = """\
  | First Header  | Second Header |
  | ------------- | ------------- |
  | Content Cell  | Content Cell  |
  | Content Cell  | Content Cell  |\
"""

MD_PLANY_UML = """\
  ```plantuml
  A --> B: MakeFood()
  B --> C: MakeSoup()
  C --> A: Food
  ```\
"""

MD_IMAGE = "  ![Sample]({path})"

ITEM_TEMPLATE = """\
active: {active}
custom1: {custom1}
custom2: {custom2}
derived: false
header: |
  {header}
level: {level}
links: {links}
normative: {normative}
ref: ''
reviewed:
text: |
{text1}

{text2}

{text3}

{text4}

{text5}
"""

LEVELS: List[Tuple[str, ...]] = [
    ("1.0", "1.0-7", "1-14"),
    ("2.0", "1-14"),
    ("3",),
    ("4", "0", "1-4"),
    ("5", "1,1,1"),
    ("6",),
    ("6.0", "1-4", "1.0-4", "1-4"),
    ("7", "1-4", "1", "1.0-4"),
]


def get_word_list() -> List[str]:
    word_site = "https://www.mit.edu/~ecprice/wordlist.10000"
    response = requests.get(word_site, timeout=10)
    return response.content.decode("utf-8").splitlines()


class LevelIterator:
    def __init__(self, total_count: int) -> None:
        self.total_count = total_count

    @staticmethod
    def _parse_trailing_zero(level: str) -> Tuple[bool, int]:
        parts = level.split(".")
        if len(parts) > 2 or (len(parts) == 2 and parts[1] != "0"):
            raise RuntimeError(f"Invalid: {level}")
        if len(parts) == 2:
            return True, int(parts[0])
        return False, int(parts[0])

    @staticmethod
    def _parse(level_conf: str) -> List[str]:
        retval = []
        parts = level_conf.split(",")
        for part in parts:
            interval = part.split("-")
            if len(interval) == 1:
                # No interval
                zero, start = LevelIterator._parse_trailing_zero(interval[0])
                end = start
            elif len(interval) == 2:
                s_zero, start = LevelIterator._parse_trailing_zero(interval[0])
                e_zero, end = LevelIterator._parse_trailing_zero(interval[1])
                zero = s_zero or e_zero
            else:
                raise RuntimeError(f"Invalid range: {interval}")
            for i in range(start, end + 1):
                retval.append(str(i) + (".0" if zero else ""))

        return retval

    @staticmethod
    def _resolve(parent: str, level: Tuple[str, ...], offset: int = 0) -> List[str]:
        retval = []
        for stage in LevelIterator._parse(level[0]):
            zero, num = LevelIterator._parse_trailing_zero(stage)
            num += offset
            retval.append(parent + str(num) + (".0" if zero else ""))

            if len(level) > 1:
                retval.extend(LevelIterator._resolve(parent + str(num) + ".", level[1:]))
        return retval

    def __iter__(self) -> Generator[str, None, None]:
        offset = 0
        count = 0
        while True:
            last_top = 0
            for tree in LEVELS:
                for level in self._resolve("", tree, offset):
                    yield level
                    count += 1
                    parts = level.split(".")
                    if len(parts) == 1 and int(parts[0]) > last_top or (len(parts) == 2 and parts[0] == "0"):
                        last_top = int(parts[0])

                    if count == self.total_count:
                        return
            offset = last_top


def gen_paragraph(word_list: List[str], seed: int, num_words: int) -> str:
    paragraph = []
    for i in range(num_words):
        word_idx = ((seed + i) * 345) % len(word_list)
        paragraph.append(word_list[word_idx])
    return " ".join(paragraph).capitalize()


def generate_tree(root: Path, num_docs: int, num_req: int, image: Path) -> None:
    word_list = get_word_list()

    prev_doc_prefix = ""
    for d_idx in range(num_docs):
        doc_prefix = "REQ-" + chr(ord("A") + d_idx)
        doc_root = root / doc_prefix
        doc_root.mkdir()
        (doc_root / ".doorstop.yml").write_text(
            DOT_DOORSTOP_TEMPLATE.format(
                prefix=doc_prefix,
                parent=f"parent: {prev_doc_prefix}" if prev_doc_prefix != "" else "",
            )
        )
        out_image_rel = "images/sample.svg"
        out_image = doc_root / out_image_rel
        out_image.parent.mkdir()
        out_image.write_bytes(image.read_bytes())
        for i_idx, level in enumerate(LevelIterator(num_req)):
            item_id = i_idx + 1

            links = ""
            if prev_doc_prefix != "":
                for i in range(i_idx % 4):
                    link_id = f"{prev_doc_prefix}-{(i_idx + i) % num_req:03}"
                    links += f"- {link_id}:\n"
            seed = d_idx + i_idx
            (doc_root / f"{doc_prefix}-{item_id:03}.yml").write_text(
                ITEM_TEMPLATE.format(
                    active=((i_idx + 3) % 20 > 0),
                    header=gen_paragraph(word_list, seed, 2 + (i_idx % 4)),
                    links="\n" + links if links != "" else "[]",
                    normative=(i_idx % 10 > 0),
                    text1="  " + gen_paragraph(word_list, seed + 1, 10 + (i_idx % 10)),
                    text2=(MD_LIST if i_idx % 2 == 0 else ""),
                    text3=(MD_TABLE if i_idx % 4 == 0 else ""),
                    text4=(MD_PLANY_UML if (i_idx + 1) % 10 == 0 else ""),
                    text5=(MD_IMAGE.format(path=out_image_rel) if (i_idx + 2) % 4 == 0 else ""),
                    level=level,
                    custom1=gen_paragraph(word_list, seed + 2, 1 + (i_idx % 10)),
                    custom2=i_idx % 2 == 0,
                )
            )

        prev_doc_prefix = doc_prefix


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=200,
        help="Max number of requirements per document",
    )
    parser.add_argument("-d", "--num-docs", type=int, default=3, help="Number of documents in tree")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    project_root = repo_root / "dist" / "sample-tree"
    if project_root.exists():
        shutil.rmtree(project_root)
    project_root.mkdir(parents=True)

    generate_tree(project_root, args.num_docs, args.count, Path(repo_root / "ui/icons/check.svg"))
    print("Tree generated at:", project_root.as_posix())


if __name__ == "__main__":
    main()
