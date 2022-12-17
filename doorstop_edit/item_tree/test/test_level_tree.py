from tempfile import TemporaryDirectory

import doorstop

from doorstop_edit.item_tree.document_item_level_tree import build_item_level_tree


def test_level_tree():
    with TemporaryDirectory() as temp_dir:
        tree = doorstop.Tree(None, root=temp_dir)
        document = tree.create_document(value="TestDoc", path=temp_dir + "/TestDoc", digits=3, sep="-")
        document.add_item(number=None, level="2.3.1.1", reorder=False)
        document.add_item(number=None, level="2.3.2.2", reorder=False)
        document.add_item(number=None, level="2.0", reorder=False)
        document.add_item(number=None, level="2.0", reorder=False)
        document.add_item(number=None, level="2.2", reorder=False)
        document.add_item(number=None, level="2.1", reorder=False)
        document.add_item(number=None, level="1.0", reorder=False)
        document.add_item(number=None, level="1.1", reorder=False)
        document.add_item(number=None, level="1.2", reorder=False)
        document.add_item(number=None, level="1.3.0", reorder=False)
        document.add_item(number=None, level="1.3.1", reorder=False)
        document.add_item(number=None, level="1.3.2", reorder=False)
        document.add_item(number=None, level="1.3.3", reorder=False)

        level_tree = build_item_level_tree(document)

        assert len(level_tree.items) == 0  # Root should not contain any items

        # Root
        assert len(level_tree.content) == 2
        assert 1 in level_tree.content
        assert 2 in level_tree.content

        # 1.x
        assert len(level_tree.content[1].content) == 3
        assert len(level_tree.content[1].items) == 1
        assert 1 in level_tree.content[1].content
        assert 2 in level_tree.content[1].content
        assert 3 in level_tree.content[1].content

        # 1.3.x
        assert len(level_tree.content[1].content[3].content) == 3
        assert 1 in level_tree.content[1].content[3].content
        assert 2 in level_tree.content[1].content[3].content
        assert 3 in level_tree.content[1].content[3].content

        # 2.x
        assert len(level_tree.content[2].content) == 3
        assert len(level_tree.content[2].items) == 2  # Two 2.0
        assert 1 in level_tree.content[2].content
        assert 2 in level_tree.content[2].content
        assert 3 in level_tree.content[2].content
