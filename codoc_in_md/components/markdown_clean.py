from __future__ import annotations

"""Custom Markdown component tweaks.

Reflex's built-in Markdown renderer spreads react-markdown element props onto most tags.
For table-related tags, react-markdown passes internal props (e.g. `isHeader`) that are
not valid DOM attributes, producing console warnings.

This module provides a small subclass that suppresses those props for table tags,
while keeping GFM + raw HTML support from Reflex's default Markdown component.
"""

from reflex.components.markdown.markdown import Markdown
from reflex.vars.base import Var


class CleanMarkdown(Markdown):
    """A Markdown component that avoids passing invalid props to DOM table tags."""

    _NO_PROPS_TAGS = (
        "ul",
        "ol",
        "li",
    )

    _TABLE_TAGS = ("table", "thead", "tbody", "tr", "th", "td")

    # react-markdown passes internal props like `isHeader` to table cells.
    # Filter those out while keeping useful props like `align`, `colSpan`, etc.
    _FILTERED_MARKDOWN_PROPS = Var(
        _js_expr="(({ isHeader, ...rest }) => rest)(props)",
        _var_type=dict,
    )

    def get_component(self, tag: str, **props):
        # Import the implementation module to reuse internal helpers/constants.
        # Use importlib to avoid resolving to a re-exported `markdown` function.
        import importlib

        md = importlib.import_module("reflex.components.markdown.markdown")

        # Largely mirrors reflex.components.markdown.markdown.Markdown.get_component,
        # but extends the "no props" list to include table tags.
        if tag not in self.component_map:
            msg = f"No markdown component found for tag: {tag}."
            raise ValueError(msg)

        special_props = [md._PROPS]
        children = [
            md._CHILDREN
            if tag != "codeblock"
            else md.ternary_operation(
                md.ARRAY_ISARRAY.call(md._CHILDREN),
                md._CHILDREN.to(list).join("\n"),
                md._CHILDREN,
            ).to(str)
        ]

        if tag in self._NO_PROPS_TAGS:
            special_props = []
        elif tag in self._TABLE_TAGS:
            special_props = [self._FILTERED_MARKDOWN_PROPS]

        children_prop = props.get("children")
        if children_prop is not None:
            children = []

        return self.component_map[tag](*children, **props).set(special_props=special_props)
