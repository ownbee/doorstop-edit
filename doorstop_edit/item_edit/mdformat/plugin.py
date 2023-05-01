from typing import Mapping

from markdown_it import MarkdownIt
from markdown_it.common.utils import normalizeReference
from markdown_it.rules_inline import StateInline
from mdformat.renderer import RenderContext, RenderTreeNode
from mdformat.renderer.typing import Postprocess, Render


def update_mdit(md: MarkdownIt) -> None:
    md.inline.ruler.before("link", "preprocess_link", preprocess_link)


def preprocess_link(state: StateInline, silent: bool) -> bool:
    """Add undefined reference links to references.

    Code for parsing is taken from `markdown-it-py/markdown_it/rules_inline/link.py`. However, no
    link nodes are added in this code, it just adds undefined reference links to the reference list
    to avoid them being escaped later.
    """
    label = None
    maximum = state.posMax

    if state.srcCharCode[state.pos] != 0x5B:  # /* [ */
        return False

    labelStart = state.pos + 1
    labelEnd = state.md.helpers.parseLinkLabel(state, state.pos, True)

    # parser failed to find ']', so it's not a valid link
    if labelEnd < 0:
        return False

    pos = labelEnd + 1

    if pos < maximum and state.srcCharCode[pos] == 0x5B:  # /* [ */
        start = pos + 1
        pos = state.md.helpers.parseLinkLabel(state, pos)
        if pos >= 0:
            label = state.src[start:pos]
            pos += 1
        else:
            pos = labelEnd + 1

    else:
        pos = labelEnd + 1

    # covers label == '' and label == undefined
    # (collapsed reference link and shortcut reference link respectively)
    if not label:
        label = state.src[labelStart:labelEnd]

    label = normalizeReference(label)

    if "references" not in state.env:
        state.env["references"] = {}

    if label not in state.env["references"]:
        if "^" in label:
            # Check if a defined footnote
            footnote_label = label.lower().replace("^", ":")
            footnote_refs = state.env.get("footnotes", {}).get("refs", {})
            if footnote_label in footnote_refs:
                # label is defined and handled by footnotes, nothing to do...
                return False
        # Add undefined reference, content does not matter since they wont be resolved/rendered in
        # the end.
        state.env["references"][label] = {
            "title": "",
            "href": "",
            "map": [0, 0],
        }
        if "undefined_references" not in state.env:
            state.env["undefined_references"] = []
        state.env["undefined_references"].append(label)

    return False


def alter_used_refs(text: str, node: RenderTreeNode, ctx: RenderContext) -> str:
    """Remove undefined_references from used_refs.

    This will avoid them being rendered in the reference list at the bottom.
    """
    if "undefined_references" in ctx.env:
        for undef_label in ctx.env["undefined_references"]:
            if undef_label in ctx.env["used_refs"]:
                ctx.env["used_refs"].remove(undef_label)

    return text


RENDERERS: Mapping[str, Render] = {}

POSTPROCESSORS: Mapping[str, Postprocess] = {"root": alter_used_refs}
