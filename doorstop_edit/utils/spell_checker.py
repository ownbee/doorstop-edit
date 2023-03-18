import re

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QTextDocument
from spellchecker import SpellChecker


class TextEditSpellChecker(QSyntaxHighlighter):
    def __init__(self, parent: QTextDocument):
        super().__init__(parent)

        self.spell = SpellChecker()

    def highlightBlock(self, text: str) -> None:

        word_list = []
        for w in text.split():
            # Remove all leading and trailing non-word characters (e.g. comma or dot).
            new = re.sub(r"^\W+|\W+$", "", w)
            if "[" in new or "]" in new:
                continue

            if len(new) > 1:
                word_list.append(new)

        unknown = self.spell.unknown(word_list)

        myClassFormat = QTextCharFormat()
        myClassFormat.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
        myClassFormat.setUnderlineColor(Qt.GlobalColor.red)

        for w in unknown:
            # Search occurences of unknown word that stands alone (not a substring).
            # Non-word characters in matching words are disregarded.
            #
            # "ointm" should not match "ointm" in appointment
            # "asdasd" should match "asdasd" in "asdasd."
            expression = QRegularExpression(rf"(?:^|[^\w])({w})(?:$|[^\w])")
            i = expression.globalMatch(text)
            while i.hasNext():
                match = i.next()
                self.setFormat(match.capturedStart(1), match.capturedLength(1), myClassFormat)
