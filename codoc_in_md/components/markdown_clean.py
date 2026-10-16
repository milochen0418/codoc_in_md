"""Custom Markdown component tweaks (Reflex 0.10).

`CleanMarkdown` is Reflex's Markdown with three changes:

- It turns on the plugins `rx.markdown` uses (GFM, math + KaTeX, raw HTML, unwrap
  images). Since Reflex 0.10 they live in rx.markdown's wrapper, not in `Markdown`.
- Table tags filter the element props react-markdown passes (older versions sent
  `isHeader`, which is not a DOM attribute) and list tags get none, so the Tailwind
  classes of the component map stay in charge.
- A `<pre>` that is not a fenced code block (`<pre><code>`) renders as a plain
  `<pre>`. Reflex's code-block handler reads the props of a single `<code>` child,
  but the Pygments HTML from `embeds.apply_hackmd_code_blocks_with_lines` puts
  `<span>`s straight into `<pre>`, which would crash the whole preview.
"""

from __future__ import annotations

import reflex as rx
from reflex.components.core.markdown_component_map import MarkdownComponentMap
from reflex.components.markdown.markdown import _CHILDREN, _PROPS, Markdown
from reflex.vars.base import Var, VarData

_NO_PROPS_TAGS = ("ul", "ol", "li")
_TABLE_TAGS = ("table", "thead", "tbody", "tr", "th", "td")

# Keep react-markdown's internal `isHeader` off table cells; keep `align`, `colSpan`, etc.
_FILTERED_TABLE_PROPS = Var(
    _js_expr="(({ isHeader, ...rest }) => rest)(props)",
    _var_type=dict,
)


class CleanMarkdown(Markdown):
    """A Markdown component that keeps invalid props off DOM tags and renders raw <pre>."""

    @classmethod
    def create(cls, *children, **props) -> rx.Component:
        plugin = rx.markdown.plugin
        props.setdefault(
            "remark_plugins",
            Var.create([plugin.math, plugin.gfm]).to(list[Var | tuple[Var, Var]]),
        )
        props.setdefault(
            "rehype_plugins",
            Var.create([plugin.katex, plugin.raw, plugin.unwrap_images]).to(
                list[Var | tuple[Var, Var]]
            ),
        )
        return super().create(*children, **props)

    def get_component(self, tag: str, **props) -> rx.Component:
        # Mirrors Markdown.get_component, with per-tag element props.
        if tag not in self.component_map:
            msg = f"No markdown component found for tag: {tag}."
            raise ValueError(msg)

        if tag in _NO_PROPS_TAGS:
            special_props = []
        elif tag in _TABLE_TAGS:
            special_props = [_FILTERED_TABLE_PROPS]
        else:
            special_props = [_PROPS]

        children = [_CHILDREN] if props.get("children") is None else []
        return self.component_map[tag](*children, **props).set(special_props=special_props)

    def format_component_map(self) -> dict[str, Var]:
        components = super().format_component_map()
        code_block = components["pre"]
        plain_pre = MarkdownComponentMap.create_map_fn_var(
            fn_body=Var(_js_expr=f"({rx.el.pre(_CHILDREN).set(special_props=[_PROPS])!s})"),
        )
        components["pre"] = Var(
            _js_expr=(
                "((args) => (args.children?.props?.node?.tagName === 'code'"
                f" ? ({code_block!s})(args) : ({plain_pre!s})(args)))"
            ),
            _var_data=VarData.merge(
                code_block._get_all_var_data(), plain_pre._get_all_var_data()
            ),
        )
        return components
