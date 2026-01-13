"""HackMD-like embed directive processing.

This module provides a small, extensible architecture to translate directives like:
  {%youtube OPqDaOsYo-U %}
into raw HTML blocks suitable for rendering inside rx.markdown.

Add new embed types by registering an implementation in EMBED_EXTENSIONS.
"""

from __future__ import annotations

from dataclasses import dataclass
import base64
import binascii
import functools
import gzip
import ipaddress
import html
import os
import re
from typing import Protocol
import json
import time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

import reflex as rx
from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse, Response


@dataclass(frozen=True, slots=True)
class EmbedDirective:
    name: str
    args: str
    raw: str


class EmbedExtension(Protocol):
    """An embed extension transforms a directive into an HTML block."""

    name: str

    def render(self, directive: EmbedDirective) -> str | None:
        """Return an HTML string if handled, otherwise None."""
        ...


@dataclass(frozen=True, slots=True)
class FencedCodeBlock:
    language: str
    code: str
    raw: str


class FencedBlockExtension(Protocol):
    """A fenced-block extension transforms a code block into an HTML block."""

    language: str

    def render(self, block: FencedCodeBlock) -> str | None:
        ...


_QUOTE_TAG_RE = re.compile(
    r"\[name=(?P<name>[^\]]+)\]\s*\[time=(?P<time>[^\]]+)\]\s*\[color=(?P<color>[^\]]+)\]"
)


_ADMONITION_START_RE = re.compile(r"^\s*:::(?P<kind>[a-zA-Z0-9_-]+)(?P<rest>.*)$")
_ADMONITION_END_RE = re.compile(r"^\s*:::\s*$")
_ADMONITION_ATTRS_RE = re.compile(r"^\s*\{(?P<attrs>[^}]*)\}\s*(?P<title>.*)$")

_EMOJI_SHORTCODES_OVERRIDES: dict[str, str] = {
    # Keep a tiny override map for edge cases / customizations.
    # Most shortcodes should be handled by the `emoji` package.
    ":tada:": "🎉",
    ":mega:": "📣",
    ":zap:": "⚡",
    ":fire:": "🔥",
    ":stuck_out_tongue_winking_eye:": "😜",
}


_EMOJIFY_JS_VERSION = "2.1.0"
_EMOJIFY_CDN_BASIC = (
    f"https://cdn.jsdelivr.net/npm/@hackmd/emojify.js@{_EMOJIFY_JS_VERSION}"
    "/dist/images/basic"
)

# Gzip(base64) of the newline-separated list of emojify.js basic emoji image names.
# Generated from: @hackmd/emojify.js@2.1.0/dist/images/basic/*.png
_EMOJIFY_BASIC_NAMES_B64_GZ = """
H4sIAGe7Y2kC/5Vc7ZLspq7971e5NVXJJDnJeRoXtmmb3bZx+Oienqe/a0my2z0z98etPQ2SjEEIEJLA+39+b95+b
37/7bfm9/c//mz+6dw8N65xHf56/obG                                                          9b3fSuOGJeQc4tqW0F99yaDUGXSfgpvbktxyd4/GhbTNbvUH0LqUwi2s45My+M2lUhMKzS4tbT/H/grYL11Ao3Pwa
+OWrqJwjzLLNsUEntYeObLRz5IKnB5M                                                          a8iTB6sr+Nm2GS/9W10KFUym4JmmeG8711/vLg2GDrF2M7iJ9/WVUrcDPz26r21eRDxCuMR0qmvybkAfz2/spKO22
V/KDsa7T98JKYzTTvkGt1OMVyMcddbt                                                          3CSwM4t1215bUcKp5qyyv4fsD0Ksa/HpTGdhDDrGo/gBrCYKPZe4mtTLNHs8b/MUUbws+MWlzY+li2DlFns3xKZrO
tc9JGm7WAoGSeB+wnRS0N7gMDGJK1LM                                                          uhUttcn1/1ZfWrcOaKfy/T5KuXF0o0c/XFiIoVDxbZcg/YazOUo1yAua/WjvoUyt4t/I/eSlRnABft2Kf8xG/gjwW
UIpSgRQhxmIzM/gvK4r+5a9LCAAWCEG                                                          smyZJCmVUgB/EGDnXT9pu3UBu/PsSEuSDJAzhiqTd0i4856/JElmKuLzY1hXobIhJFPcWkMgtAar6dHPIYODcPVMw
hqQzTOq790GME7uE821OYxoKmA+IynT                                                          gJXczRiHtg+YCv4F4dRvE8TP0kLHVKdIBP4Vr2RJYKxuDE3mWtyr4Gxst4hB1eUiC65AhawjABHHzXO2Qad0bq9o8
UOoi07u1/r2J2faGjqDdOH8v5v78tpr                                                          eavkh9d+YE+RtsOE5VieaZQiFhFGYY7r8DZBPfrhbXHrK+EejZRzXJjfL1h2ACqqpUYQqBcmAOxDUVkmkho5A+MCk
UhpJItLT6AtrsuCSbow4QuVyw35nT9Z                                                          dqIgiM0qiLzJ2gJO7Y5VRFmNc7yh8xHzJ7mAx7oQkebydvF+kLIpDIf0wyw4JoorGDrqJuD+0mM1AYp9H+dA4OrXv
XsVddQwi36Fnsgl1b4EclPnjgkUUmH7                                                          7SXFtbxQMtoGAbsSlwi2CPx0HGourRTAQhI1IqT8jcYFfJkfTe/6gvd7h8WFmeDXAfLuOQcWDAREJgg73LsFmxZTb
GSaafcvs8NAgbJpMWx4rGIdZi8ZG8Ea                                                          HzBbIqtbI+lbKJh4sjsDSQFLcW16aRxr+RJmTo0PxcI6+DPYDtiNB6oR0GLNfsbGkjKrxfgWZPJ7b1g55uCamS2bG
7Gpq+6TdF8M95XbYMYi8etwflS31wfQ                                                          rT6xJ7MbifqMKeAx7kSSbNMCYHuwyQ40l7WyQZocK/N50BSVtn1COZHbFLalQj/DQsBscdwAKA3ow0xrhTUn6MHFC
TtssaYecg+rXzAgUGsVT6A0ARdR54lb                                                          345krw8ypA0qRnKG9mSycbgwhllVgc1JkMJ61eWAZ+zZHDYuR3DPjfV3y37b8z92aH/y+0F53/ODsgP25Hjwh2U7/
qdlO/6XZTv+H8t2/G/Ldvwfy3b8v5Yp                                                          njGWolIM5iMd+at/7MRjawNepfMwoy6upxQr9E6PQaWC4l5eHFQBgChDHi8XDhSywDIz9qi7l5JYUrRDAS0cl7hsy
eedstXCIYnrBYs1yE4vGKwabKoCYs4L                                                          MCZXaNPgzdy8aJEz0t5jumqVJcW5va6xk+I3v8JQ7T2VeCKn8Ros4wyIkQ1v/D3U4tJVGiu2farTGYuKKM1VzVR6q
uKUcoXJDfDOH0Y7wS7vsYZCocIfCOce                                                          s7ZdqIn7JIb5nqPvai6pDKBI4xDYVoqolaayrB+uyEBrOj9xrNAnliGAQdA723jwJ3oX1etIpkcushGyndpjzCkvG
KO6TUDt3okGMFwT9SFFRm0C7IF5QylB                                                          H0OYj9Z/QIWsozxkW1DA0lPkcQEXtbTxAv3KmQDjhtUMMAFh1l7XcCEiKlSzzHyMSLHPYR3vq3GghAdq3gG6ohn41
4ehxmr6YaCxpW7KQvnqEENr+jn0tMQx                                                          h56rfYAqY4WStSHPVP3ArthV2mNODsEtUaxXKBEVjYP+5JYjW5I9B3chQ7HQ+MA8PSMtm/c3oX5+PjTVMRhiu6KqO
RRpKo78vSPB2kuSZabbhMU0xEjSdysG                                                          tHHi4huwh1PMm5e6kxsxvTSz5rjikGIFQpYw4mV/Ax5leK1MxAxGZQn2mW4WgEwfDxWW9lCXTbbH4TY0HqYP1r93M
LQa2sH4kQdMZsEprgsQtyPYRIHlHc0B                                                          T8aRP3qZpfGy6PzTlKO+UgOssHp5ABvmCjqME9SWr43/5Xu8BOcCRl/fbjMsDWDbJDXOl8YrlxhgDw0wR+wHO2BjK
lYSJpmvKUoCKWKvQhPs2I5vMXMmX6R3                                                          GIUR027VyYclAN0gegnwNkcxc+hOEjVdN3MA/MPz9xbWt7x5309vXe26WYj7XAeYGw5Iu7l5UegWl0DLVjH1feIdR
huslnIiqmLAMzAoS940fdjyqRQtnZZF                                                          oIYqPJ3TE/CMmQW7CAv6ScY0j3QqnhQs4xaMduLsukAFfXq4QTJS9U+Ma/H97fODKLZX+xSAqiNxMjOa/MZugfmxc
FPBEiJ1q2svz7H6H8iDpLAkV7gx7gJ4                                                          CTNJGMo9HHBxH80FU/JSZ+SY/hfMmNm/0YPOTwxKMa6uHoTzjvNmO87xCHuswQN4QxlY2DshkrkdM1a/VHBxaTlh8
CounPtP0liFc0V+VZpkhiye2jj0O64T                                                          9kv9W6AzvSPQAP1e8CiSe2yVZwFkmVkHVupA48vQQtf4+RRdntY4x/H5fsulaKCNiyIjN+UdWdzRE3VwDb7R3E7Ho
084R/LSqhzDFs3tHQbqLAjqDh7mB0xL                                                          GDatKLDnvirGdu86WJJFkQtsFdYT5gXeB9RUVnhLkcqFoyWNI2n9ChdeYcqUJRMmExQY5iR162wUuoxFVhiUwneSL
VeqXfEOmbTilxDiKsC4eOF6f05uOY+w                                                          17+53vLB8p1+sXy0PFg+W75YHi3/1/Jkeba8WF4tv1v+Yfmn5p2zvLPc+OmMn8746YyfbrLc+Op+WW58davlxl9nf
HXGV2d8dTfLja/uYbnx1RtfvcmpN756                                                          46c3fnrjpzd+sMdpbvLqja/e+OqNr36z3PjrTU698dUbX73Jqzf+euNvMPkM1v/B2h2svcHaGay8t354e88b/54W0
mqd88aMN2F5E5Y35i7WyYs1erHGLtbY                                                          xd4fTXijDepo9Y/W+GiNjya80eodTWij1Tua0EabZONev/E1Gl+jCWs0IU0mjMnqmayeyd6f7P3J3g8mnGB8BuMzG
D/B6glWT7D+BuMrWL3B5Bas/l9Wzy97                                                          /5e998sG/2rPryaPq8njavK42ntXa/e6v2ftXa3fV+v31QZ7NvnPJv/Z+jdbvbPJZ7Z6ZuN7Nr5nk8tsk3G2+herd
7H6FpPXYv1YrB+L9WOxdhaT42L9Waw/                                                          i8ljsX4txs9i/CzGz2L8LMbPYv1ebHEsO3/W/9X4XI2v1RbtavytJofV+FqNj9X4WI2P1dpdrd5o/G9W/2b1b1b/Z
vVv1v/N+r9ZO5v1e7P6N+vnZv3crF+b                                                          9edfaycZf8nKJ+MrWfls5bKNd+73PJbn6s57blxn4zYbt9mkkm11Z+M+G/fZep+tF9m4ytabbNxl60220co2Stl6l
U2axbguxm0x/orxVYyvYvwU46cYP8X4                                                          KcZPMX6K8VOMj2J8FJNWsfartV+tvWr1VauvWn+q8V3tvZu9dzO+9y31ZvXcTI43q+dmo3WH5WFV3i1/2KufVuWns
fCprEqpPM3i1lxmeBLt4GGLkx4kEHWB                                                          F7I92iHIYMmJEiwJc9bpw18YFqZtPQsxuyoWD7xF/KgvY9RTCwIbTP6Cd2CXiOGg/jXQUmGtW7iDcZXCOC+AJImYx
vQUblL1h1klgGkLqaGywYnm8d+F7g6c                                                          Otrv3AYEylMK1AESEbwkMsfQg1j91c9b5cPKIKvYQjt0NoHAYIJPW9PajGx0AKfYfka6laNf+ONJiBqL4wRXrBnDR
ROLv4whucvFa4VA5kYcKgk+BKjMcY7d                                                          7s7AOYLzvuZGgt/IIhqnPTgytDVG2KpMII8xpsBo2JjcxoLi9OmJpcISUFPQ+BA4uxm2GWAJkBzeoRD+rT4bFhbXU
06ABF3XHVt3t/zpb+nhjPhuwPTsgg7l                                                          D8XpMKsfJa5C5onEWAPd6BELhCcVPXyZiYe2iXY9oOXIpI2Np3wn/M5wz0QKXe9GouXiSEqDGqkmuoRhoFGtIarWg
lJStINZqjlmLIE80eIFxADkxPAO3Fl4                                                          EoMdMgomq0FReKfbhM5ngqldY+tv2OVV8JJihfUxqbCVIFJ4goyCKdr5HdrqDK0qoBS9PfRksZVzFyUwCC+H6eKXG
E2CNWfKaazPL1vzXx62Ma2O0SorhSle                                                          87m2pc4lbHDP9J0PI2/zsxhcvwkLbmKYK24yMH6GQ6yjcp9C8ToEoKeumUIXcg/VOEEptZ2EOVcGJgQXDwpe0xSRY
oZT1GgOvqJAPNTUkwdJecLL2YrVKMcb                                                          AOAIeVFsABnSQiY1lkzdBIU4Qd/IsnxCLRWfKjfOKAbqmtdwXTZcujTyrBU9r+N4BK4mVZKh5WpuH7FqhENEBKcWA
vBwfAh9cwk3hrX4JF8ZWARkhVHd4COX                                                          /dS64eagNGH/Us+FlefPJbkHwD4uErLYQ0thhb61MWZAcT8UPtMzut6z6BoZC24Y6UopyqF1kPndwAQNn+7qHq5la
MxDL/5iICye0M1ZynMZi1Yd+Bi7OZye                                                          oyd46qnzfsUHf7IQkIssGti0vyBSCe5dnYNfxyWJn56BAOjdpnE4gwtG4RoYGWok6M1E3tZcqj9gDUPJUtxpumh3L
ENHH7Gfa7iHS4K6anQLk7SVfW3jWVFz                                                          hb4Gh/GKtlMzuw6zbBeMakk9Y9Wj8BPFQrZGgqKAkjoRv/rt3yinPYvnEHaiBbiO1FMNtlLuJzPXJRjzl8IQj0xUO
vBylj5XuQChiB5cawhSCBoWbC0sSJIe                                                          yul9EA3SccuZ/UIGfeRv4xjNHnOwzTPPCps5dMk1Ynow4DYrKLvLAbV6xMOTL0l4hQG7XOolXDiHPXZsqJ7MAfiU1
niX43mChNcx1cEQY3hb3Bo5JGD9nO4U                                                          LkD0zTEMJctUdYOAPOkV8v2skp5XbiRwIxFha+N40GMVxhfKbt98LbmBVrrEU3a1paRrS7NgT8LP7thIAGpx06+4k
hxmnspabrP4QNWUoGxfKNiUjPgMIn4J                                                          If6fAcRn+PBL8PAcOvwpcHgOG34LGp5ChqeA4Wu48Idg4SlU+FOg8EuY8BwkfAkRvgQIv4cHj+DgKTR4Cgw+w4LPo
OBLSPAcEKSVg9+b3JsZFcR04Pp7E5tD                                                          Kffnw8eeHzDs7iKhxL2QxJXdvBz4btsSGWHJVW5tdEJfCTKIJBTGv992k+tMW7D9addAo8W6Awc3gjwfwSbdWxb1+
bb3+NDdRKhTjyczLGS2dZfjkyy0c9+/                                                          9v+Fl2/8fOdpsfV2Frr5MG+HrXcm3qHAEyeTCmyLtezv8WRgf08JMlZvciNG8LoeoofXoTaAYjUdosn3sBzDBQNqe
6kTftzB6B1C5EMMWWfy4hp+63g77A0P                                                          8xtPFB9H+XgW3YF9oRyyeaI/lDgVS5g0++iprc1S0JB6X0YsZXkGzYyJbgV5YrrD0HddheygN9uMjRM67wabrJyeY
x3DbNxiDmIcGxW2vFsebeI9IiOV+uEH                                                          GRyzuKqDM4BFeKI9BZb1EuHC3Xfegqe5JXvD4nhALscuC9Ug77/Avm4rNnOYQiBmFrIVAFucBzwdjR8No/OeGM857
Y7h4keHZCbr2PqQrNi+7T4eJgVvEPLC                                                          KXZfPGICcwtWnOR8J5klBuM44fWAnVttLQFzT+vtxXdp6DY+Wt6RpfPJi0fM4axDXcaOJwdSAQ8FQaCprGdeurMIQ
a1wsWGFQA8IAG0rzY7CUXZpsToWeOxw                                                          K9TyWmKGv8isHNcWl8iDr/a4IkNClBeKgehOFNVPTHrAZdpe6q/Q7Cv2ANrntcOD1DuYH8eLpJA/I2Sv6TuyW/CtX
ZNa4sOhejp9MIjAVc00v5BNOr+qXro5                                                          rMqdsILXAwHrVOsVpBVNMhBCaOENIe5bqxjRKLjRv8J+mr3cchVBrvDaSmA+Om6cdnVvUDtNXbLVp6N0LQw7GHLnT
w2/HTjZeyBlMY8arCm59fZ0tXPDGdhg                                                          65fLnMxFpJiM9FHXgk1tB3QPAzbyghithdNcykrgKSeAzcOFkLuMQs+L3lRZI9Vm4Qi1ok1ByWy9eIlG7ICd4ZtDf
PN6LCyPUV+1uyZxLk1s4nsDZwQLBTYG                                                          bw1wIMgnTY4NYxnpdNnpd8So8GZAg7bQimhWtib3Hnnvh9NbztRavXGusD0FZCWPG8cQeNw9KdhHUSXypHHpHYiaI
XJ/8qAV9xEarmU5eRYhCHQ+3hOCqtLn                                                          +TTAKdR+YgPqDOjLCquLgtU4xYH2n9j6eO3w/+IdzH80G1wzarGN95rN3q+bonpWX6HqiaaGpoTeGiCUeQO8RBgEk
zxbeQSYCQxOp91hkTec7xx+7kitm+ns                                                          nAINpB4K4oy0cqtz490CuRuQJ6kr5w0da+2SFAj31uKHcodkHxoiE1PMF3kELj32ndmyd+ZjZQvQujRVwS71u4xlk
ndS5n0JeQIF/NzEDB+ixTvV7trJh51l                                                          +Pct7PngvIsZ9bg2/krgRd2WttgLmYGlDA4uL1QzTWwcZK+QoBh2OfxG/t6ZtLL8YCmjLagBjQ5u2CY4kuHz0zV6P
BwvvJqm8hdnRj4EUFDu/CuonojCdTuA                                                          Fm09p/4G5cFW6GXB3ZKbaucbKoSdXBRVOv2YV51BrERklQMcsU6hm2Y/EsaC3jtPN37jXGeC6dNRVED8uGLLt6UMt
Hxy6DCD2LhkOQsgbcm9jK0mmgS6qoBQ                                                          aNgbNk6eul+F4nAGmAkisuYIlSbXdaFY9o689xqK0iCUyMRA2fNE+4IyhKjpfqNbENfr5kANl7hybXOzahTGCsdgy
w1kdZQJ8nq15W9yL9Zus3QSnbmoMjTa                                                          V/h8RQdmEw1i/1IgN2YB768u/HnyiK5765N8CpA01wAHBiMwKMva/Ow+NNeLZ4mR80E+Iuk69t9vXmrb1OTi23RMs
XISl+krsy8GUes/ipdLmSgZ59sRxQHf                                                          HkYO6FNgTAt6stmb42RkomsxaTjO8WaxIrwOyRKY8y+hEguMSLsWDKGp3qTYRbvGmKLcnuS1IV5c3drnFi003oOSe
2LNfrOI30JNnhFH2EhH0Aadt1KcT0h4                                                          aTxFNZ9bPb5JXBTtPl0T715RihV/Y/doj3MYeiisyhwVy6l091vWmWHu7PA3YsLrN09ZAgioMDMezkAoDGBm99CzM
CwwpDCwsUb8E2ppdK+rPAv5EjAy2fG+                                                          WiTwYfZt7uXkSvVb7ifec9UMvDDaThQuI5ZTs9uNNMI2rjsFyKLGRTUTrQAQYm1ofiHpqVjP12AyI6l84o84PeBB/
JwMhx9KNPsUeIPz+12v4wKb7tLcQMDL                                                          xM9/sE/BC8FSkwv2oC2cBwSSpJj0LSddxmayMSWPEy8EMVtLlPMqyoWKWAaGKRPOp+HEzZe7fOLoIBGHEvMZRv2BF
ZlxDxLulJ8eiYmPirTqlR6ZtVQ6ZJ8T                                                          keo5C4X2Fu/dj+xt+ODvuAMpUdd8Dfx5geDWYmTf3k/wHyf4zxP81wn+D+BKcTAV609Mmk4Mzzxz+swQmoyQAa3rY
WMtcdAjFSE/mNHRoaMhGJcI7I19y7aO                                                          7uQ9tmtULN/F8VgHiJxhHV8gKvoSqFXSl0CtEqkA9w99fiDp7sq2vaY6aQk9LDsoXw7PTrFokZLow69T0grJMC+Bc
4+pVamGeqYDw5SLevX+8ymFFfO459cI                                                          Q3v4Y0qUrYag+Egcb8DYaq76Frdby4VbMNMSb3Ls8OsZmkN2xYDSkcmRADd0aEZ0MKw3J5VuyDKzcWI0ilC6UlSap
x3IBjxD9hLFfa5pi+lKvi+VLx/g7DFt                                                          +7iP6KDqbgvKTBC3wHcE6ZHtH+dgrQ87jX6L4eifBnT0iyYxZfOud/6tcPuxZviZGfPLhcvN+czvIVWXyYJC8iYR2
KvA75LaqtBb+krBy4O7aZ1JXtalgLyK                                                          UTeHzqeCSUUrlF9VwIGRqC0IGBc4UHfq2Yb36jUgX0XAvGbfyX3FXCrNBwwl1ulY/TfCywnKt4d3+3aFh8EMu8LaO
cU3QLlc9COBoh93wS+AHYcVOOzT7Uk4                                                          2Tuk6rp64k9/GJheWWhO9/TV/di/xrH8uGos05yF0kVeg1ZkKp5DfEYY9LMRSVveSc8G21q+e8/74WK9SqiPdem+g
XyF9yoSfHCx+qa8Jf/RqOHLzTJkzqHB                                                          7lbKnl1cH5EMDsnVU660lotbXeeKU2etiCVCnVWww2IOicuJAcePt80p6APit5Y+0NcmSUNL2nYjnyw9Vf/5AnOZb
BhFvMDS64bKtc7Zsy+jMgljTM24bTU2                                                          U6a6dFnUn4LwIgCIFSgjKV0Xt1C/DEdG11TSd2SLFsTCKCHtoZWyNAWeP0vH6yNi7nHs4axzHGza8qM8/HgnvfBwe
4h7blNIbGoVepITDOb0WMzMKsoV03dm                                                          aFPUeeU5O+1tmnD0Z850XU6Fnyiu8qAu29TYjszYQeFSeEgmIaYh8cjrQOWCrSoCpMvGLqpdUCod7wIZ0prUg+tSE
+MbyHjgWm5NudP4HtRvOx3Woeg98rcb                                                          yQQX/zWuSyq8qG/0+tf73+9I//ztH6R/df9p6n/++O1vpH+TgvS/SP0/vzX179/ff0f61x9/IP3vP4Td366p1+b4m
msHKL9RjNknab+Vv9pqq6tb5JMrmTJ0                                                          j+oqXyzqRKirTA1MqrrxOxj90l4f5ebW7Cczx5cqr0N8m1CIp5Mau4gDSvKofY8iKsJbQAD5dQqyNMYGHge/pmTOY
eUcuuVmj+bfnZ5ovnxfZcSRrgjMTKOl                                                          VV/AoOln342qZ3GLsZIuFzdHw+SYQkANPd9hXjIRA1A+TREn0Ch63WKnPFr5YOnuPn7i7OM7Z33D84gH0kG+UtIjm
5YnOJjfd1i/XtP3RiIlsjPB7F2c4r3E                                                          NezOx/P+ihHUVdxZlMVryIvVprSX78CV9NMX3a9PzrQfir1+WX0Ps0RtjRNuPZ1dBFE+ZHeaoIsIelt83OmaO+9na
eDBjmD06Gk/jzmf+O20+7nAo3k9ulHs                                                          5eRPSeezP6PsUSk7yDmf/30lxetBej0DfKXuZyCnw6MvB0dfD40Mt9NAxZ7ngWf8LKXjjFDR45TwhJ6Lfz04VOrX4
z6lfjvweyWfjvzsgR36KfZy7Gek08Gf                                                          UcyjVux5+Ge4Hf8Zth8AKvpyBKikQ23EH44Bjfh/HQTa4y9z6acZ9W1EfxzXn0f3eSioh4FH1FTR79HQg34OhgpR/
s+QwpMxQyeVKo/J7jHNcEHcRoi3ORu7                                                          56ft84vMe5IvuDQm9dE8vDjh6gs84JZDKO2Dd5cesLc/3WpnWp+o89NDzxvqU2w+5drr+ZjMTu4/Pz//F2FBh1nZR
gAA
"""


@functools.lru_cache(maxsize=1)
def _emojify_basic_names() -> frozenset[str]:
    blob = re.sub(r"\s+", "", _EMOJIFY_BASIC_NAMES_B64_GZ)
    raw = gzip.decompress(base64.b64decode(blob))
    names = raw.decode("utf-8").splitlines()
    return frozenset(n for n in names if n)


_EMOJI_SHORTCODE_RE = re.compile(r":(?P<name>[a-zA-Z0-9_+\-]+):")


def _emoji_img_html(name: str) -> str:
    safe_name = _escape_attr(name)
    return (
        f'<img class="emoji" alt=":{safe_name}:" '
        f'src="{_EMOJIFY_CDN_BASIC}/{safe_name}.png" '
        'style="display:inline-block;width:1.25em;height:1.25em;vertical-align:-0.2em"/>'
    )


def _replace_emoji_shortcodes(text: str) -> str:
    """Replace :shortcode: emojis.

    HackMD/CodiMD uses emoji-cheat-sheet style shortcodes (via emojify.js).
    Instead of maintaining a massive mapping table, we rely on the Python
    `emoji` library's alias database (GitHub/cheatsheet-style).
    """

    if not text:
        return text

    try:
        import emoji  # type: ignore
    except Exception:
        emoji = None

    def _flag_from_code(code: str) -> str:
        code = code.upper()
        if len(code) != 2 or not code.isalpha():
            return f":flag_{code.lower()}:"
        base = 0x1F1E6
        return chr(base + (ord(code[0]) - ord("A"))) + chr(
            base + (ord(code[1]) - ord("A"))
        )

    def _replace_token(m: re.Match[str]) -> str:
        raw_name = m.group("name")
        raw_token = f":{raw_name}:"

        # 1) Exact overrides.
        if raw_token in _EMOJI_SHORTCODES_OVERRIDES:
            return _EMOJI_SHORTCODES_OVERRIDES[raw_token]

        # 2) Flags (unicode only for ISO-3166 2-letter country codes).
        # emojify.js also includes non-country flags like flag-england/flag_scotland,
        # which should fall back to images instead of unicode derivation.
        m_flag = re.match(r"^flag[-_](?P<cc>[a-zA-Z]{2})$", raw_name)
        if m_flag:
            return _flag_from_code(m_flag.group("cc"))

        # 3) Prefer emojify.js image if the shortcode exists there.
        # HackMD/CodiMD uses emojify.js images for shortcodes; using Unicode here
        # makes preview diverge from HackMD and breaks DOM-based tests.
        names = _emojify_basic_names()
        if raw_name in names:
            return _emoji_img_html(raw_name)
        alt = raw_name.replace("_", "-")
        if alt in names:
            return _emoji_img_html(alt)

        # 4) Unicode alias via python-emoji (best effort fallback).
        if emoji is not None:
            normalized = raw_name.replace("-", "_")
            if normalized.startswith("female_"):
                normalized = "woman_" + normalized[len("female_") :]
            elif normalized.startswith("male_"):
                normalized = "man_" + normalized[len("male_") :]

            unicode_candidate = emoji.emojize(f":{normalized}:", language="alias")
            if unicode_candidate != f":{normalized}:":
                return unicode_candidate

        return raw_token

    return _EMOJI_SHORTCODE_RE.sub(_replace_token, text)


_HACKMD_IMG_SIZE_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\((?P<inside>[^\)]*?\s=\s*\d*\s*x\s*\d*[^\)]*?)\)",
    re.IGNORECASE,
)


def _parse_hackmd_img_size(inside: str) -> tuple[str, str | None, int | None, int | None] | None:
    """Parse HackMD image destination with optional title and size.

    Supports forms like:
      url =200x200
      url "title" =200x
      <url> =x200

    Returns (url, title, width_px, height_px) or None if not parseable.
    """

    s = (inside or "").strip()
    if not s:
        return None

    # URL: first token (or <...> form).
    url = ""
    rest = ""
    if s.startswith("<"):
        end = s.find(">")
        if end <= 1:
            return None
        url = s[1:end].strip()
        rest = s[end + 1 :].strip()
    else:
        m = re.match(r"^(?P<url>\S+)(?P<rest>.*)$", s)
        if not m:
            return None
        url = (m.group("url") or "").strip()
        rest = (m.group("rest") or "").strip()

    if not url:
        return None

    # Size token can appear anywhere in the remaining text.
    m_size = re.search(
        r"(?:^|\s)=\s*(?P<w>\d*)\s*x\s*(?P<h>\d*)(?=\s|$)",
        rest,
        flags=re.IGNORECASE,
    )
    if not m_size:
        return None

    raw_w = (m_size.group("w") or "").strip()
    raw_h = (m_size.group("h") or "").strip()
    if not raw_w and not raw_h:
        return None

    width = int(raw_w) if raw_w.isdigit() else None
    height = int(raw_h) if raw_h.isdigit() else None

    # Remove the size token from the rest.
    rest_wo_size = (rest[: m_size.start()] + rest[m_size.end() :]).strip()

    # Optional title in quotes (single/double, including curly). Prefer the first quoted segment.
    title: str | None = None
    m_title = re.search(
        r'(?:"(?P<t1>.*?)"|\'(?P<t2>.*?)\'|\u201c(?P<t3>.*?)\u201d)',
        rest_wo_size,
    )
    if m_title:
        title = m_title.group("t1") or m_title.group("t2") or m_title.group("t3")
    elif rest_wo_size:
        # If something remains but isn't quoted, treat it as not-a-title.
        title = None

    return url, title, width, height


def apply_hackmd_image_sizes(markdown_text: str) -> str:
    """Support HackMD-style image sizing: `![alt](url =200x200)`.

    This is not CommonMark; we rewrite it into raw HTML `<img ...>` so react-markdown
    can render it while preserving sizes.

    Skips fenced code blocks and inline code spans.
    """

    text = markdown_text or ""
    if not text:
        return text

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0

    in_code = False
    fence_char = ""
    fence_len = 0

    def _maybe_open_fence(line: str) -> tuple[str, int] | None:
        m = re.match(r"^\s*(?P<fence>`{3,}|~{3,})(?P<info>[^\n]*)\n?$", line)
        if not m:
            return None
        f = m.group("fence")
        return f[0], len(f)

    def _is_fence_close(line: str, ch: str, ln: int) -> bool:
        return re.match(rf"^\s*{re.escape(ch)}{{{ln},}}\s*\n?$", line) is not None

    inline_code_re = re.compile(r"(`+)([^`]*?)\1")

    def _replace_in_text(buf: str) -> str:
        def _repl(m: re.Match[str]) -> str:
            alt = m.group("alt") or ""
            inside = m.group("inside") or ""
            parsed = _parse_hackmd_img_size(inside)
            if parsed is None:
                return m.group(0)
            url, title, width, height = parsed

            safe_url = _escape_attr(url)
            safe_alt = _escape_attr(alt)
            attrs = [f'src="{safe_url}"', f'alt="{safe_alt}"', 'loading="lazy"']
            if title:
                attrs.append(f'title="{_escape_attr(title)}"')

            style_parts = ["max-width:100%"]
            if width is not None and width > 0:
                attrs.append(f'width="{width}"')
                style_parts.append(f"width:{width}px")
            if height is not None and height > 0:
                attrs.append(f'height="{height}"')
                style_parts.append(f"height:{height}px")
            if height is None:
                # Preserve aspect ratio unless explicitly overridden.
                style_parts.append("height:auto")

            attrs.append(f'style="{_escape_attr(";".join(style_parts))}"')
            return f"<img {' '.join(attrs)} />"

        return _HACKMD_IMG_SIZE_RE.sub(_repl, buf)

    while i < len(lines):
        line = lines[i]

        if not in_code:
            opened = _maybe_open_fence(line)
            if opened is not None:
                fence_char, fence_len = opened
                in_code = True
                out.append(line)
                i += 1
                continue
        else:
            if _is_fence_close(line, fence_char, fence_len):
                in_code = False
                fence_char = ""
                fence_len = 0
            out.append(line)
            i += 1
            continue

        # Replace outside inline code spans.
        replaced: list[str] = []
        last = 0
        for m in inline_code_re.finditer(line):
            replaced.append(_replace_in_text(line[last : m.start()]))
            replaced.append(line[m.start() : m.end()])
            last = m.end()
        replaced.append(_replace_in_text(line[last:]))
        out.append("".join(replaced))
        i += 1

    return "".join(out)


def apply_hackmd_emojis(markdown_text: str) -> str:
    """Apply emoji shortcode replacement globally, skipping fenced code blocks."""

    text = markdown_text or ""
    if not text:
        return text

    # Skip fenced code blocks (``` or ~~~, length 3+).
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0

    in_code = False
    fence_char = ""
    fence_len = 0

    def _maybe_open_fence(line: str) -> tuple[str, int] | None:
        m = re.match(r"^\s*(?P<fence>`{3,}|~{3,})(?P<info>[^\n]*)\n?$", line)
        if not m:
            return None
        f = m.group("fence")
        return f[0], len(f)

    def _is_fence_close(line: str, ch: str, ln: int) -> bool:
        return re.match(rf"^\s*{re.escape(ch)}{{{ln},}}\s*\n?$", line) is not None

    inline_code_re = re.compile(r"(`+)([^`]*?)\1")

    while i < len(lines):
        line = lines[i]

        if not in_code:
            opened = _maybe_open_fence(line)
            if opened is not None:
                fence_char, fence_len = opened
                in_code = True
                out.append(line)
                i += 1
                continue
        else:
            if _is_fence_close(line, fence_char, fence_len):
                in_code = False
                fence_char = ""
                fence_len = 0
            out.append(line)
            i += 1
            continue

        # Replace outside inline code spans.
        replaced: list[str] = []
        last = 0
        for m in inline_code_re.finditer(line):
            replaced.append(_replace_emoji_shortcodes(line[last : m.start()]))
            replaced.append(line[m.start() : m.end()])
            last = m.end()
        replaced.append(_replace_emoji_shortcodes(line[last:]))
        out.append("".join(replaced))
        i += 1

    return "".join(out)


def _render_admonition_body_html(body_lines: list[str]) -> str:
    # Convert lines into paragraphs; preserve blank lines.
    paragraphs: list[list[str]] = []
    buf: list[str] = []
    for line in body_lines:
        if not line.strip():
            if buf:
                paragraphs.append(buf)
                buf = []
            continue
        buf.append(line)
    if buf:
        paragraphs.append(buf)

    parts: list[str] = []
    for para in paragraphs:
        rendered_lines = []
        for raw in para:
            s = _replace_emoji_shortcodes(raw)
            rendered_lines.append(_format_inline_md_minimal(s))
        parts.append(
            "<p style=\"margin:0\" class=\"text-gray-700 leading-relaxed\">"
            + "<br/>".join(rendered_lines)
            + "</p>"
        )
    # Add spacing between paragraphs.
    return "<div style=\"display:flex;flex-direction:column;gap:0.5rem\">" + "".join(parts) + "</div>"


def _admonition_styles(kind: str) -> tuple[str, str, str]:
    """Return (border_color, bg_color, title_color) for built-in kinds."""

    k = (kind or "").lower()
    if k == "success":
        return ("#16a34a", "#dcfce7", "#166534")
    if k == "info":
        return ("#0284c7", "#e0f2fe", "#075985")
    if k == "warning":
        return ("#f59e0b", "#fef9c3", "#92400e")
    if k == "danger":
        return ("#ef4444", "#fee2e2", "#991b1b")
    # Fallback
    return ("#cbd5e1", "#f8fafc", "#334155")


def apply_hackmd_admonitions(markdown_text: str) -> str:
    """Convert HackMD-style admonition blocks into raw HTML.

    Supported forms:
      :::success\n...\n:::
      :::info\n...\n:::
      :::warning\n...\n:::
      :::danger\n...\n:::
      :::spoiler Title\n...\n:::
      :::spoiler {state="open"} Title\n...\n:::
    """

    text = markdown_text or ""
    if not text:
        return text

    # We skip inside fenced code blocks (``` or ~~~, length 3+).
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0

    in_code = False
    fence_char = ""
    fence_len = 0

    def _maybe_open_fence(line: str) -> tuple[str, int] | None:
        m = re.match(r"^\s*(?P<fence>`{3,}|~{3,})(?P<info>[^\n]*)\n?$", line)
        if not m:
            return None
        f = m.group("fence")
        return f[0], len(f)

    def _is_fence_close(line: str, ch: str, ln: int) -> bool:
        return re.match(rf"^\s*{re.escape(ch)}{{{ln},}}\s*\n?$", line) is not None

    while i < len(lines):
        line = lines[i]

        if not in_code:
            opened = _maybe_open_fence(line)
            if opened is not None:
                fence_char, fence_len = opened
                in_code = True
                out.append(line)
                i += 1
                continue
        else:
            if _is_fence_close(line, fence_char, fence_len):
                in_code = False
                fence_char = ""
                fence_len = 0
            out.append(line)
            i += 1
            continue

        m = _ADMONITION_START_RE.match(line.rstrip("\r\n"))
        if not m:
            out.append(line)
            i += 1
            continue

        kind = (m.group("kind") or "").strip()
        rest = (m.group("rest") or "").strip()

        supported = {"success", "info", "warning", "danger", "spoiler"}
        if kind.lower() not in supported:
            out.append(line)
            i += 1
            continue

        # Collect body until closing :::
        body: list[str] = []
        i += 1
        while i < len(lines) and not _ADMONITION_END_RE.match(lines[i].rstrip("\r\n")):
            body.append(lines[i].rstrip("\r\n"))
            i += 1
        # Consume closing line if present.
        if i < len(lines) and _ADMONITION_END_RE.match(lines[i].rstrip("\r\n")):
            i += 1

        if kind.lower() == "spoiler":
            title = rest
            is_open = False
            am = _ADMONITION_ATTRS_RE.match(rest)
            if am:
                attrs = am.group("attrs") or ""
                title = (am.group("title") or "").strip()
                if re.search(
                    r"\bstate\s*=\s*(?:[\"“”]open[\"“”]|'open'|open)",
                    attrs,
                ):
                    is_open = True

            safe_title = _format_inline_md_minimal(_replace_emoji_shortcodes(title or ""))
            body_html = _render_admonition_body_html(body)

            open_attr = " open" if is_open else ""
            # Styled details/summary similar to HackMD.
            out.append(
                "\n"
                + f"<details{open_attr} style=\"border:1px solid #e5e7eb;border-radius:0.5rem;background:#f3f4f6;overflow:hidden;margin:1rem 0\">"
                + f"<summary style=\"cursor:pointer;user-select:none;padding:0.75rem 1rem;font-weight:600;color:#374151\">{safe_title or 'Details'}</summary>"
                + f"<div style=\"padding:0.75rem 1rem;background:#ffffff\">{body_html}</div>"
                + "</details>\n"
            )
            continue

        border, bg, title_color = _admonition_styles(kind)
        title_text = kind.capitalize()
        # If user wrote a single-line title in first content line, HackMD doesn't require it.
        # We follow the provided syntax: content body contains the title.

        body_html = _render_admonition_body_html(body)
        out.append(
            "\n"
            + "<div "
            + "style=\""
            + f"border-left:4px solid {border};"
            + f"background:{bg};"
            + "padding:0.9rem 1rem;"
            + "border-radius:0.5rem;"
            + "margin:1rem 0;"
            + "\""
            + ">"
            + f"<div style=\"font-weight:700;color:{title_color};margin-bottom:0.35rem\">{title_text}</div>"
            + body_html
            + "</div>\n"
        )

    return "".join(out)


@dataclass
class _QuoteNode:
    depth: int
    lines: list[str]
    children: list["_QuoteNode"]
    name: str | None = None
    time: str | None = None
    color: str | None = None


def _count_blockquote_depth(line: str) -> tuple[int, str] | None:
    """Return (depth, content) if line is a blockquote line, else None.

    Accepts `>` and `> ` and nesting like `>>` / `> >`.
    """

    i = 0
    n = len(line)
    depth = 0
    while i < n:
        # Optional leading spaces are allowed before a quote marker.
        while i < n and line[i] in " \t":
            i += 1
        if i < n and line[i] == ">":
            depth += 1
            i += 1
            # Optional single space after >
            if i < n and line[i] == " ":
                i += 1
            continue
        break

    if depth == 0:
        return None
    return depth, line[i:]


def _parse_quote_tree(lines: list[str]) -> list[_QuoteNode]:
    roots: list[_QuoteNode] = []
    stack: list[_QuoteNode] = []

    for raw in lines:
        parsed = _count_blockquote_depth(raw)
        if parsed is None:
            # Not a quote line (shouldn't happen here).
            continue
        depth, content = parsed

        while stack and stack[-1].depth > depth:
            stack.pop()

        if not stack or stack[-1].depth < depth:
            node = _QuoteNode(depth=depth, lines=[], children=[])
            if stack:
                stack[-1].children.append(node)
            else:
                roots.append(node)
            stack.append(node)

        # Now stack[-1].depth == depth
        stack[-1].lines.append(content.rstrip("\r\n"))

    return roots


def _extract_quote_meta(node: _QuoteNode) -> None:
    """Extract [name/time/color] tags from the node's lines.

    HackMD uses a separate line inside the quote to specify metadata.
    We remove that line from rendered content.
    """

    kept: list[str] = []
    for line in node.lines:
        m = _QUOTE_TAG_RE.search(line.strip())
        if m and node.name is None and node.time is None and node.color is None:
            node.name = m.group("name").strip()
            node.time = m.group("time").strip()
            node.color = m.group("color").strip()
            continue
        kept.append(line)
    node.lines = kept

    for child in node.children:
        _extract_quote_meta(child)


def _format_inline_md_minimal(text: str) -> str:
    """Minimal inline markdown rendering for quote bodies.

    Supports **bold** and `code`.
    """

    raw = text or ""

    # Preserve emojify-style <img class="emoji" .../> tags inserted by our emoji
    # replacement logic; everything else gets HTML-escaped.
    emoji_imgs: list[str] = []

    def _stash_img(m: re.Match[str]) -> str:
        emoji_imgs.append(m.group(0))
        return f"@@COD0C_EMOJI_IMG_{len(emoji_imgs) - 1}@@"

    s = re.sub(r"<img\s+class=\"emoji\"[^>]*?/?>", _stash_img, raw)
    s = html.escape(s, quote=False)
    # Inline code first.
    s = re.sub(r"`([^`]+)`", lambda m: f"<code class=\"px-1 py-0.5 rounded bg-gray-100 text-gray-800\">{html.escape(m.group(1), quote=False)}</code>", s)
    # Bold.
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)

    for idx, tag in enumerate(emoji_imgs):
        s = s.replace(f"@@COD0C_EMOJI_IMG_{idx}@@", tag)
    return s


def _render_quote_node_html(node: _QuoteNode) -> str:
    color = (node.color or "#CBD5E1").strip()  # default similar to border-gray-300
    safe_color = _escape_attr(color)
    safe_name = html.escape(node.name or "", quote=False)
    safe_time = html.escape(node.time or "", quote=False)

    # Split into paragraphs by blank lines.
    paragraphs: list[str] = []
    buf: list[str] = []
    for line in node.lines:
        if not line.strip():
            if buf:
                paragraphs.append("\n".join(buf))
                buf = []
            continue
        buf.append(line)
    if buf:
        paragraphs.append("\n".join(buf))

    body_parts: list[str] = []
    for para in paragraphs:
        rendered = "<br/>".join(_format_inline_md_minimal(x) for x in para.split("\n"))
        body_parts.append(f"<p class=\"mb-3 last:mb-0 text-gray-700 leading-relaxed\">{rendered}</p>")

    for child in node.children:
        body_parts.append(_render_quote_node_html(child))

    user_icon = (
        "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\" "
        "style=\"width:1rem;height:1rem;color:#9CA3AF;flex:none\" "
        "fill=\"none\" stroke=\"currentColor\" "
        "stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">"
        "<path d=\"M20 21a8 8 0 0 0-16 0\"/>"
        "<circle cx=\"12\" cy=\"8\" r=\"4\"/>"
        "</svg>"
    )
    clock_icon = (
        "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\" "
        "style=\"width:1rem;height:1rem;color:#9CA3AF;flex:none\" "
        "fill=\"none\" stroke=\"currentColor\" "
        "stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">"
        "<circle cx=\"12\" cy=\"12\" r=\"9\"/>"
        "<path d=\"M12 7v6l3 2\"/>"
        "</svg>"
    )

    meta_html = ""
    if node.name or node.time:
        # HackMD-like meta row with user + clock icons.
        parts: list[str] = []
        if node.name:
            parts.append(
                "<span style=\"display:inline-flex;align-items:center;gap:0.25rem\">"
                + user_icon
                + f"<span style=\\\"font-weight:500;color:#374151\\\">{safe_name}</span>"
                + "</span>"
            )
        if node.time:
            parts.append(
                "<span style=\"display:inline-flex;align-items:center;gap:0.25rem\">"
                + clock_icon
                + f"<span>{safe_time}</span>"
                + "</span>"
            )
        meta_html = (
            "<div class=\"mt-2 text-sm text-gray-500\" "
            "style=\"display:flex;align-items:center;gap:0.75rem;flex-wrap:nowrap;white-space:nowrap;overflow-x:auto\">"
            "<span style=\"color:#9CA3AF\">—</span>"
            + "".join(parts)
            + "</div>"
        )

    # Use a dedicated wrapper so nested quotes look consistent.
    return (
        f"<div class=\"my-4 pl-4 border-l-4\" style=\"border-left-color:{safe_color}\">"
        + "".join(body_parts)
        + meta_html
        + "</div>"
    )


def apply_hackmd_blockquote_labels(markdown_text: str) -> str:
    """Render HackMD-style blockquote labels.

    Detects quote blocks that include a metadata line of the form:
      [name=...] [time=...] [color=...]
    and converts the whole blockquote region into styled HTML.

    Nested quotes are supported.
    """

    text = markdown_text or ""
    if not text:
        return text

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0

    while i < len(lines):
        if _count_blockquote_depth(lines[i]) is None:
            out.append(lines[i])
            i += 1
            continue

        # Collect a contiguous quote block.
        start = i
        i += 1
        while i < len(lines) and _count_blockquote_depth(lines[i]) is not None:
            i += 1
        block_lines = lines[start:i]

        # Only transform if we see at least one tag line anywhere in the block.
        if not any(_QUOTE_TAG_RE.search((_count_blockquote_depth(l) or (0, ""))[1].strip()) for l in block_lines):
            out.extend(block_lines)
            continue

        roots = _parse_quote_tree(block_lines)
        for r in roots:
            _extract_quote_meta(r)

        html_blocks = "\n".join(_render_quote_node_html(r) for r in roots)

        # Ensure HTML is treated as a block.
        out.append("\n" + html_blocks + "\n")

    return "".join(out)


_DIRECTIVE_RE = re.compile(
    r"\{\%\s*(?P<name>[A-Za-z0-9_-]+)(?:\s+(?P<args>.*?))?\s*\%\}",
    re.IGNORECASE | re.DOTALL,
)

_FENCED_BLOCK_RE = re.compile(
    # Only match *exactly* triple-backtick fences.
    # This avoids breaking markdown that uses longer fences like ````` to show ``` literally.
    r"```(?!`)(?P<info>[^\n]*)\r?\n(?P<body>.*?)(?:\r?\n)```(?!`)",
    re.DOTALL,
)


def _escape_attr(value: str) -> str:
    """Escape a string for use in an HTML attribute."""

    # html.escape(..., quote=True) does not escape single quotes.
    return html.escape(value, quote=True).replace("'", "&#x27;")


def _extract_youtube_id(value: str) -> str | None:
    value = (value or "").strip()
    if not value:
        return None

    # Common ID format is 11 chars; accept a safe subset.
    if re.fullmatch(r"[A-Za-z0-9_-]{6,64}", value):
        return value

    try:
        parsed = urlparse(value)
    except Exception:
        return None

    host = (parsed.netloc or "").lower()
    path = parsed.path or ""

    # https://www.youtube.com/watch?v=VIDEO_ID
    if "youtube.com" in host:
        query = parse_qs(parsed.query or "")
        vid = (query.get("v") or [""])[0]
        if re.fullmatch(r"[A-Za-z0-9_-]{6,64}", vid):
            return vid
        # https://www.youtube.com/embed/VIDEO_ID
        if path.startswith("/embed/"):
            candidate = path.split("/embed/", 1)[1].split("/", 1)[0]
            if re.fullmatch(r"[A-Za-z0-9_-]{6,64}", candidate):
                return candidate

    # https://youtu.be/VIDEO_ID
    if host.endswith("youtu.be"):
        candidate = path.lstrip("/").split("/", 1)[0]
        if re.fullmatch(r"[A-Za-z0-9_-]{6,64}", candidate):
            return candidate

    return None


_OEMBED_CACHE: dict[str, tuple[float, str]] = {}
_OEMBED_TTL_S = 60 * 60 * 24


def _backend_base_url() -> str:
    """Base URL for the Reflex backend (used by embed iframes).

    Default matches Reflex dev backend port. Override via env for other deployments.
    """

    return os.getenv("CODOC_BACKEND_BASE_URL", "http://localhost:8000").rstrip("/")


def _encode_code_b64(code: str) -> str:
    """Encode text to URL-safe base64 without padding."""

    raw = (code or "").encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _smart_quotes(text: str) -> str:
    """Best-effort smart quotes (like HackMD/Remarkable typographer).

    Applies to plain text only (caller must exclude code spans/blocks).
    """

    out: list[str] = []
    n = len(text)

    def _prev_nonspace(i: int) -> str:
        j = i - 1
        while j >= 0 and text[j].isspace():
            j -= 1
        return text[j] if j >= 0 else ""

    def _next_nonspace(i: int) -> str:
        j = i + 1
        while j < n and text[j].isspace():
            j += 1
        return text[j] if j < n else ""

    for i, ch in enumerate(text):
        if ch == '"':
            prev = _prev_nonspace(i)
            nxt = _next_nonspace(i)
            is_open = (not prev) or prev in "([{" or prev in "\n\r\t" or prev == "-"
            # If followed by punctuation or end, treat as closing.
            if not nxt or nxt in ")]}.,:;!?":
                is_open = False
            out.append("\u201c" if is_open else "\u201d")
            continue

        if ch == "'":
            prev = _prev_nonspace(i)
            nxt = _next_nonspace(i)
            # Apostrophe in the middle of a word.
            if prev.isalnum() and nxt.isalnum():
                out.append("\u2019")
                continue
            is_open = (not prev) or prev in "([{" or prev in "\n\r\t" or prev == "-"
            if not nxt or nxt in ")]}.,:;!?":
                is_open = False
            out.append("\u2018" if is_open else "\u2019")
            continue

        out.append(ch)

    return "".join(out)


def _apply_typography_to_text(text: str) -> str:
    """Apply HackMD-like typographic replacements to plain text."""

    if not text:
        return text

    s = text

    # Symbols.
    s = re.sub(r"\((?:c)\)", "\u00a9", s, flags=re.IGNORECASE)
    s = re.sub(r"\((?:r)\)", "\u00ae", s, flags=re.IGNORECASE)
    s = re.sub(r"\((?:tm)\)", "\u2122", s, flags=re.IGNORECASE)
    s = re.sub(r"\((?:p)\)", "\u00a7", s, flags=re.IGNORECASE)
    s = s.replace("+-", "\u00b1")

    # Punctuation.
    s = s.replace("---", "\u2014")  # em dash
    s = s.replace("--", "\u2013")  # en dash
    s = re.sub(r"\.{3}", "\u2026", s)  # ellipsis

    # Collapse excessive punctuation (HackMD-like).
    s = re.sub(r"!{4,}", "!!!", s)
    s = re.sub(r"\?{4,}", "???", s)
    s = re.sub(r",{2,}", ",", s)

    # Quotes.
    s = _smart_quotes(s)

    return s


def _normalize_curly_quotes_to_straight(text: str) -> str:
    """Convert curly quotes (smart quotes) to straight quotes.

    HackMD content sometimes contains typographic quotes inside Markdown link/image
    titles (e.g. `![alt](url ”title”)`). CommonMark parsers generally only accept
    straight quotes for titles, so we normalize them in markdown syntax regions.
    """

    if not text:
        return text
    return (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )


def apply_hackmd_typography(markdown_text: str) -> str:
    """Apply HackMD-like typography substitutions to markdown.

    - Skips fenced code blocks and inline code spans.
    - Leaves embed directives `{% ... %}` untouched.
    """

    text = markdown_text or ""
    out_parts: list[str] = []

    # Be tolerant like HackMD/markdown-it: allow 1+ dashes.
    # We will normalize to 3 dashes later so remark-gfm reliably parses tables.
    _TABLE_DELIM_RE = re.compile(
        r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)+\|?\s*$"
    )

    _TABLE_CELL_RE = re.compile(r"(?P<lead>\|\s*)(?P<cell>:?-{1,}:?)(?=\s*\||\s*$)")

    def _normalize_table_delim_line(line: str) -> str:
        """Normalize a GFM table delimiter line.

        HackMD accepts as few as 1 dash; remark-gfm expects 3+. To make preview match
        HackMD behavior, we keep alignment markers but pad dashes to at least 3.
        """

        raw = line.rstrip("\r\n")
        suffix = line[len(raw) :]

        def _pad(cell: str) -> str:
            left = ":" if cell.startswith(":") else ""
            right = ":" if cell.endswith(":") else ""
            dash_count = max(0, len(cell) - len(left) - len(right))
            dashes = "-" * max(3, dash_count)
            return f"{left}{dashes}{right}"

        # Ensure the line has leading/trailing pipes for consistent parsing.
        if "|" not in raw:
            return line

        s = raw
        if not s.strip().startswith("|"):
            s = "|" + s
        if not s.strip().endswith("|"):
            s = s + "|"

        def _repl(m: re.Match[str]) -> str:
            return f"{m.group('lead')}{_pad(m.group('cell'))}"

        s = _TABLE_CELL_RE.sub(_repl, s)
        return s + suffix

    def _iter_table_aware_parts(buf: str) -> list[tuple[bool, str]]:
        """Split a string into (is_table, text) parts.

        This prevents typography transforms from breaking GFM tables.
        """

        if not buf:
            return [(False, buf)]

        lines = buf.splitlines(keepends=True)
        parts: list[tuple[bool, str]] = []
        i = 0

        def _is_header_line(line: str) -> bool:
            s = line.strip()
            if "|" not in s:
                return False
            # Require some non-syntax content.
            return any(ch not in "|:- " for ch in s)

        def _is_delim_line(line: str) -> bool:
            return _TABLE_DELIM_RE.match(line.rstrip("\r\n")) is not None

        while i < len(lines):
            if i + 1 < len(lines) and _is_header_line(lines[i]) and _is_delim_line(lines[i + 1]):
                start = i
                # Normalize delimiter line to keep table parsing stable.
                lines[i + 1] = _normalize_table_delim_line(lines[i + 1])
                i += 2
                while i < len(lines) and lines[i].strip() and ("|" in lines[i]):
                    i += 1
                parts.append((True, "".join(lines[start:i])))
                continue

            # Normal text: accumulate until next table start.
            start = i
            i += 1
            while i < len(lines):
                if i + 1 < len(lines) and _is_header_line(lines[i]) and _is_delim_line(lines[i + 1]):
                    break
                i += 1
            parts.append((False, "".join(lines[start:i])))

        return parts

    def _process_noncode(segment: str) -> str:
        if not segment:
            return segment

        # Preserve raw HTML tags exactly; typography (especially smart quotes)
        # must not modify attribute quotes inside <...>.
        html_tag_re = re.compile(r"</?[A-Za-z][^>]*?>")

        def _apply_typography_preserving_html(s: str) -> str:
            if not s:
                return s
            out: list[str] = []
            pos2 = 0
            for m2 in html_tag_re.finditer(s):
                out.append(_apply_typography_to_text(s[pos2 : m2.start()]))
                out.append(m2.group(0))
                pos2 = m2.end()
            out.append(_apply_typography_to_text(s[pos2:]))
            return "".join(out)

        # Markdown link/image aware: avoid transforming destinations/titles.
        # Smart-quote conversion inside `( ... )` breaks markdown parsing.
        _INLINE_LINK_OR_IMAGE_RE = re.compile(
            r"(?P<label>!?\[[^\]]*\])\((?P<dest>[^\)\n]*)\)"
        )
        _REF_DEF_LINE_RE = re.compile(r"(?m)^\s*\[[^\]]+\]\s*:\s*[^\n]*$")

        def _apply_typography_preserving_inline_links_and_images(s: str) -> str:
            """Apply typography while preserving inline link/image destinations.

            This prevents smart-quote conversion from breaking markdown parsing inside
            `( ... )` link/image syntax, including optional titles.
            """

            if not s:
                return s

            out2: list[str] = []
            pos4 = 0
            for m4 in _INLINE_LINK_OR_IMAGE_RE.finditer(s):
                before = s[pos4 : m4.start()]
                if before:
                    out2.append(_apply_typography_preserving_html(before))

                label = m4.group("label")
                dest = m4.group("dest")
                out2.append(label + "(" + _normalize_curly_quotes_to_straight(dest) + ")")
                pos4 = m4.end()

            out2.append(_apply_typography_preserving_html(s[pos4:]))
            return "".join(out2)

        def _apply_typography_preserving_md_syntax(s: str) -> str:
            if not s:
                return s

            parts_out: list[str] = []
            pos3 = 0

            # Protect reference definition lines first.
            for m3 in _REF_DEF_LINE_RE.finditer(s):
                before = s[pos3 : m3.start()]
                if before:
                    parts_out.append(_apply_typography_preserving_inline_links_and_images(before))

                raw_line = m3.group(0)
                parts_out.append(_normalize_curly_quotes_to_straight(raw_line))
                pos3 = m3.end()

            tail = s[pos3:]
            if not tail:
                return "".join(parts_out)

            # Within remaining text, also protect inline link/image destinations.
            parts_out.append(_apply_typography_preserving_inline_links_and_images(tail))
            return "".join(parts_out)

        # Do not transform inside embed directives.
        parts: list[str] = []
        pos = 0
        for m in _DIRECTIVE_RE.finditer(segment):
            before = segment[pos : m.start()]
            raw = m.group(0)
            parts.append(before)
            parts.append(raw)
            pos = m.end()
        parts.append(segment[pos:])

        # Apply typography to each non-directive chunk, preserving inline code and tables.
        for i, chunk in enumerate(parts):
            if i % 2 == 1:
                out_parts.append(chunk)
                continue

            for is_table, buf in _iter_table_aware_parts(chunk):
                if is_table:
                    out_parts.append(buf)
                    continue

                # Split on inline code spans (backticks) and only transform non-code.
                j = 0
                while j < len(buf):
                    tick = buf.find("`", j)
                    if tick == -1:
                        out_parts.append(_apply_typography_preserving_md_syntax(buf[j:]))
                        break
                    # Find matching tick.
                    end = buf.find("`", tick + 1)
                    if end == -1:
                        out_parts.append(_apply_typography_preserving_md_syntax(buf[j:]))
                        break
                    out_parts.append(_apply_typography_preserving_md_syntax(buf[j:tick]))
                    out_parts.append(buf[tick : end + 1])
                    j = end + 1
        return ""

    # Robust fenced-block skipping: supports 3+ backticks/tildes and won't be confused by
    # longer fences like ````` used to show ``` literally.
    fence_open_re = re.compile(r"^(?P<indent>\s{0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
    lines = text.splitlines(keepends=True)
    i = 0
    buf: list[str] = []

    def _flush_buf():
        if not buf:
            return
        _process_noncode("".join(buf))
        buf.clear()

    while i < len(lines):
        line = lines[i].rstrip("\r\n")
        m_open = fence_open_re.match(line)
        if not m_open:
            buf.append(lines[i])
            i += 1
            continue

        _flush_buf()

        indent = m_open.group("indent")
        fence = m_open.group("fence")
        fence_char = fence[0]
        fence_len = len(fence)
        close_re = re.compile(rf"^{re.escape(indent)}{re.escape(fence_char)}{{{fence_len},}}\s*$")

        out_parts.append(lines[i])
        i += 1
        while i < len(lines) and not close_re.match(lines[i].rstrip("\r\n")):
            out_parts.append(lines[i])
            i += 1
        if i < len(lines):
            out_parts.append(lines[i])
            i += 1

    _flush_buf()
    return "".join(out_parts)


_FA_I_TAG_RE = re.compile(
    r"<i(?P<before>[^>]*?)\sclass=(?P<q>[\"\'])(?P<cls>[^\"\']*\bfa\b[^\"\']*)(?P=q)(?P<after>[^>]*)>",
    flags=re.IGNORECASE,
)

_FA_I_ELEMENT_RE = re.compile(
    r"<i(?P<before>[^>]*?)\sclass=(?P<q>[\"\'])(?P<cls>[^\"\']*\bfa\b[^\"\']*)(?P=q)(?P<after>[^>]*)>\s*</i>",
    flags=re.IGNORECASE,
)


def apply_hackmd_fontawesome_icons(markdown_text: str) -> str:
    """Preserve HackMD-style Font Awesome icon info through sanitization.

    Some Markdown renderers sanitize raw HTML and strip the `class` attribute,
    which breaks icons like:
      <i class="fa fa-file-text"></i>

    We keep the original class list in a data attribute (`data-codoc-fa-class`), which
    is typically allowed, and a small client script can re-apply the class.

    This transform skips fenced code blocks.
    """

    text = markdown_text or ""
    if not text:
        return text

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0

    in_code = False
    fence_char = ""
    fence_len = 0

    def _maybe_open_fence(line: str) -> tuple[str, int] | None:
        m = re.match(r"^\s*(?P<fence>`{3,}|~{3,})(?P<info>[^\n]*)\n?$", line)
        if not m:
            return None
        f = m.group("fence")
        return f[0], len(f)

    def _is_fence_close(line: str, ch: str, ln: int) -> bool:
        return re.match(rf"^\s*{re.escape(ch)}{{{ln},}}\s*\n?$", line) is not None

    def _element_repl(m: re.Match[str]) -> str:
        before = m.group("before")
        q = m.group("q")
        cls = (m.group("cls") or "").strip()
        after = m.group("after")

        safe_cls = _escape_attr(cls)
        already_annotated = re.search(
            r"\bdata-codoc-fa-class\s*=", before + after, flags=re.IGNORECASE
        )

        # Convert <i> to <span> so it survives stricter sanitizers.
        # Font Awesome targets `.fa` class on any element.
        data_attr = "" if already_annotated else f' data-codoc-fa-class="{safe_cls}"'
        return f"<span{before} class={q}{cls}{q}{after}{data_attr}></span>"

    def _tag_repl(m: re.Match[str]) -> str:
        before = m.group("before")
        q = m.group("q")
        cls = (m.group("cls") or "").strip()
        after = m.group("after")

        # If already annotated, do nothing.
        if re.search(r"\bdata-codoc-fa-class\s*=", before + after, flags=re.IGNORECASE):
            return m.group(0)

        safe_cls = _escape_attr(cls)
        return f"<i{before} class={q}{cls}{q}{after} data-codoc-fa-class=\"{safe_cls}\">"

    while i < len(lines):
        line = lines[i]

        if not in_code:
            opened = _maybe_open_fence(line)
            if opened is not None:
                fence_char, fence_len = opened
                in_code = True
                out.append(line)
                i += 1
                continue
        else:
            if _is_fence_close(line, fence_char, fence_len):
                in_code = False
                fence_char = ""
                fence_len = 0
            out.append(line)
            i += 1
            continue

        # Prefer rewriting full icon elements (<i ...></i>) into <span ...></span>.
        s = _FA_I_ELEMENT_RE.sub(_element_repl, line)
        # Fallback: annotate opening tags so a client script can restore class.
        s = _FA_I_TAG_RE.sub(_tag_repl, s)
        out.append(s)
        i += 1

    return "".join(out)


_CODE_FENCE_RE = re.compile(
    # Only match *exactly* triple-backtick fences. See `_FENCED_BLOCK_RE`.
    r"```(?!`)(?P<info>[^\n]*)\r?\n(?P<body>.*?)(?:\r?\n)```(?!`)",
    re.DOTALL,
)


def apply_hackmd_code_fence_options(markdown_text: str) -> str:
    """Apply HackMD-like code fence options.

    Supports (HackMD-style), rewritten into a markdown-parser-friendly first token:
    - ```lang=101  -> ```lang-linenos-101
    - ```lang=     -> ```lang-linenos-1
    - ```lang=+    -> ```lang-linenos-<previous_end+1>
    - ```lang!     -> ```lang-wrap
    - ```!         -> ```markdown-wrap

    This function rewrites the fence info string only; it does not modify code content.
    """

    text = markdown_text or ""
    last_end_line: int | None = None

    fence_open_re = re.compile(r"^(?P<indent>\s{0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0

    def _count_body_lines(body_lines: list[str]) -> int:
        return len(body_lines)

    while i < len(lines):
        line = lines[i].rstrip("\r\n")
        m_open = fence_open_re.match(line)
        if not m_open:
            out.append(lines[i])
            i += 1
            continue

        indent = m_open.group("indent")
        fence = m_open.group("fence")
        info = (m_open.group("info") or "").rstrip("\r")
        fence_char = fence[0]
        fence_len = len(fence)
        close_re = re.compile(rf"^{re.escape(indent)}{re.escape(fence_char)}{{{fence_len},}}\s*$")

        j = i + 1
        body_lines: list[str] = []
        while j < len(lines) and not close_re.match(lines[j].rstrip("\r\n")):
            body_lines.append(lines[j])
            j += 1

        # No closing fence: emit verbatim.
        if j >= len(lines):
            out.append(lines[i])
            out.extend(body_lines)
            break

        stripped = info.strip()
        if stripped:
            parts = stripped.split(None, 1)
            token = parts[0]
            rest = parts[1] if len(parts) > 1 else ""

            wrap = False
            if token.endswith("!"):
                wrap = True
                token = token[:-1]
            if wrap and not token:
                token = "markdown"

            start_line: int | None = None
            if "=" in token:
                base, opt = token.split("=", 1)
                base = base.strip()
                opt = opt.strip()
                if opt == "+":
                    start_line = (last_end_line + 1) if last_end_line else 1
                elif opt.isdigit():
                    start_line = int(opt)
                else:
                    start_line = 1
                token = base

            out_token = token
            if start_line is not None:
                out_token = f"{token}-linenos-{start_line}"
            if wrap:
                out_token = f"{out_token}-wrap" if out_token else "markdown-wrap"

            new_info = out_token if not rest else f"{out_token} {rest}".rstrip()
            line_end = lines[i][len(lines[i].rstrip("\r\n")) :]
            out.append(f"{indent}{fence}{new_info}{line_end}")

            if start_line is not None:
                count = _count_body_lines(body_lines)
                if count > 0:
                    last_end_line = start_line + count - 1
                else:
                    last_end_line = start_line
        else:
            out.append(lines[i])

        out.extend(body_lines)
        out.append(lines[j])
        i = j + 1

    return "".join(out)


def apply_hackmd_code_blocks_with_lines(markdown_text: str) -> str:
    """Render fenced code blocks into HTML with syntax highlighting and optional line numbers.

    This is the pragmatic way to support HackMD-style options in Reflex today:
    - `=`, `=101`, `=+` (already normalized by `apply_hackmd_code_fence_options`) -> line numbers
    - `!` (normalized to `-wrap`) -> wrap long lines

    Output is raw HTML that relies on `rehypeRaw` (already enabled) to render.
    """

    text = markdown_text or ""

    try:
        from pygments import highlight  # type: ignore
        from pygments.formatters.html import HtmlFormatter  # type: ignore
        from pygments.lexers import get_lexer_by_name  # type: ignore
        from pygments.lexers.special import TextLexer  # type: ignore
    except Exception:
        # If pygments isn't installed, keep the markdown as-is.
        return text

    aliases = {
        "js": "javascript",
        "ts": "typescript",
        "py": "python",
        "sh": "bash",
        "shell": "bash",
        "zsh": "bash",
        "yml": "yaml",
        "md": "markdown",
        "html": "html",
        "xml": "xml",
        "c++": "cpp",
        "c#": "csharp",
        "ps1": "powershell",
        "console": "text",
    }

    fence_open_re = re.compile(
        r"^(?P<indent>\s{0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$"
    )

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0

    def _parse_info(info: str) -> tuple[str, bool, bool, int]:
        """Return (language, wrap, show_linenos, linenostart)."""

        stripped = (info or "").strip()
        if not stripped:
            return ("text", False, False, 1)

        token = stripped.split(None, 1)[0]
        wrap = False
        if token.endswith("-wrap"):
            wrap = True
            token = token[: -len("-wrap")]

        show_linenos = False
        linenostart = 1
        m_ln = re.match(r"^(?P<base>.+?)-linenos-(?P<start>\d+)$", token, flags=re.IGNORECASE)
        if m_ln:
            show_linenos = True
            linenostart = int(m_ln.group("start"))
            token = m_ln.group("base")

        lang = aliases.get(token.strip().lower(), token.strip().lower())
        if not lang:
            lang = "text"

        return (lang, wrap, show_linenos, linenostart)

    def _render_block(info: str, code: str) -> str:
        lang, wrap, show_linenos, linenostart = _parse_info(info)

        try:
            lexer = get_lexer_by_name(lang)
        except Exception:
            lexer = TextLexer()

        formatter = HtmlFormatter(
            linenos="table" if show_linenos else False,
            linenostart=linenostart,
            noclasses=True,
        )

        highlighted = highlight(code, lexer, formatter)
        # Ensure the block scrolls horizontally by default.
        # If wrap is requested, allow wrapping inside <pre>.
        if wrap:
            # Add `white-space: pre-wrap` into the first <pre ...> style.
            highlighted = re.sub(
                r"(<pre\b[^>]*style=\")",
                r"\1white-space: pre-wrap; word-break: break-word; ",
                highlighted,
                count=1,
                flags=re.IGNORECASE,
            )
            # If there was no inline style attribute, add one.
            highlighted = re.sub(
                r"(<pre\b(?![^>]*style=))",
                r"\1 style=\"white-space: pre-wrap; word-break: break-word;\"",
                highlighted,
                count=1,
                flags=re.IGNORECASE,
            )

        return (
            "<div style=\"margin-top: 1em; margin-bottom: 1em; overflow-x: auto;\">"
            + highlighted
            + "</div>"
        )

    while i < len(lines):
        line = lines[i].rstrip("\r\n")
        m_open = fence_open_re.match(line)
        if not m_open:
            out.append(lines[i])
            i += 1
            continue

        indent = m_open.group("indent")
        fence = m_open.group("fence")
        fence_char = fence[0]
        fence_len = len(fence)
        info = m_open.group("info") or ""
        j = i + 1
        body_lines: list[str] = []

        fence_close_re = re.compile(
            rf"^{re.escape(indent)}{re.escape(fence_char)}{{{fence_len},}}\s*$"
        )
        while j < len(lines) and not fence_close_re.match(lines[j].rstrip("\r\n")):
            body_lines.append(lines[j])
            j += 1

        # No closing fence: treat as normal text.
        if j >= len(lines):
            out.append(lines[i])
            out.extend(body_lines)
            break

        code = "".join(body_lines)
        code = code.rstrip("\r\n")
        out.append(_render_block(info, code) + "\n")
        i = j + 1

    return "".join(out)


def _fetch_oembed_html(*, endpoint: str, target_url: str) -> str | None:
    """Fetch oEmbed HTML with a tiny in-memory cache."""

    cache_key = f"{endpoint}|{target_url}"
    now = time.time()
    cached = _OEMBED_CACHE.get(cache_key)
    if cached and now - cached[0] < _OEMBED_TTL_S:
        return cached[1]

    full_url = endpoint
    if "?" in endpoint:
        full_url = endpoint + "&" + urlencode({"url": target_url, "format": "json"})
    else:
        full_url = endpoint + "?" + urlencode({"url": target_url, "format": "json"})

    try:
        req = Request(full_url, headers={"User-Agent": "codoc-in-md"})
        with urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    html_snippet = data.get("html") if isinstance(data, dict) else None
    if isinstance(html_snippet, str) and html_snippet.strip():
        _OEMBED_CACHE[cache_key] = (now, html_snippet)
        return html_snippet
    return None


_GIST_CACHE: dict[str, tuple[float, str]] = {}


def _build_gist_js_url(value: str) -> str | None:
    v = (value or "").strip()
    if not v:
        return None

    # HackMD shorthand: user/gist_id
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9]+", v):
        return f"https://gist.github.com/{v}.js"

    # Full gist URL.
    if v.lower().startswith("https://"):
        try:
            parsed = urlparse(v)
        except Exception:
            return None
        host = (parsed.netloc or "").lower()
        if "gist.github.com" not in host:
            return None

        # Ensure the `.js` suffix is applied to the *path* (not appended after query
        # params like `?file=...`). Preserve any existing query string.
        path = (parsed.path or "").rstrip("/")
        if not path:
            return None
        if not path.endswith(".js"):
            path = path + ".js"
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )

    return None


def _extract_gist_id(value: str) -> str | None:
    v = (value or "").strip()
    if not v:
        return None

    # HackMD shorthand: user/gist_id
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9]+", v):
        return v.split("/", 1)[1]

    # Full gist URL.
    if v.lower().startswith("https://"):
        try:
            parsed = urlparse(v)
        except Exception:
            return None
        host = (parsed.netloc or "").lower()
        if "gist.github.com" not in host:
            return None
        parts = [p for p in (parsed.path or "").split("/") if p]
        if not parts:
            return None
        candidate = parts[-1]
        if candidate.endswith(".js"):
            candidate = candidate[: -len(".js")]
        return candidate or None

    return None


def _fetch_gist_html(gist_id: str) -> str | None:
    now = time.time()
    cached = _GIST_CACHE.get(gist_id)
    if cached and now - cached[0] < _OEMBED_TTL_S:
        return cached[1]

    api_url = f"https://api.github.com/gists/{gist_id}"
    try:
        req = Request(
            api_url,
            headers={
                "User-Agent": "codoc-in-md",
                "Accept": "application/vnd.github+json",
            },
        )
        with urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    files = (data or {}).get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict) or not files:
        return None

    parts: list[str] = ["<div class=\"my-4 w-full\">"]
    for filename, meta in files.items():
        if not isinstance(meta, dict):
            continue
        content = meta.get("content")
        if not isinstance(content, str):
            continue
        safe_name = html.escape(str(filename), quote=True)
        safe_content = html.escape(content)
        parts.append(
            f"<div class=\"mb-3\"><div class=\"text-sm font-semibold text-gray-700 mb-1\">{safe_name}</div>"
        )
        parts.append(
            "<pre class=\"overflow-auto text-sm bg-gray-50 border border-gray-200 rounded p-3\">"
            f"{safe_content}</pre></div>"
        )
    parts.append("</div>")

    rendered = "".join(parts)
    _GIST_CACHE[gist_id] = (now, rendered)
    return rendered


class YouTubeEmbed:
    name = "youtube"

    def render(self, directive: EmbedDirective) -> str | None:
        video_id = _extract_youtube_id((directive.args or "").strip())
        if not video_id:
            return None

        embed_url = f"https://www.youtube.com/embed/{video_id}"

        # Inline CSS for reliable aspect ratio (no Tailwind plugin dependency and avoids
        # accidental <p> wrapping collapsing the iframe height).
        return (
            "\n<div class=\"my-4 w-full\" "
            "style=\"position:relative;padding-bottom:56.25%;height:0;overflow:hidden;\">"
            f"<iframe src=\"{embed_url}\" "
            "title=\"YouTube video\" frameborder=\"0\" "
            "allow=\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share\" "
            "allowfullscreen "
            "style=\"position:absolute;top:0;left:0;width:100%;height:100%;\"></iframe>"
            "</div>\n"
        )


class VimeoEmbed:
    name = "vimeo"

    def render(self, directive: EmbedDirective) -> str | None:
        value = (directive.args or "").strip()
        if not value:
            return None

        # Accept either numeric ID or a vimeo URL.
        video_id: str | None = None
        if re.fullmatch(r"\d{3,20}", value):
            video_id = value
        else:
            try:
                parsed = urlparse(value)
            except Exception:
                return None
            host = (parsed.netloc or "").lower()
            if "vimeo.com" not in host:
                return None
            candidate = (parsed.path or "").strip("/").split("/", 1)[0]
            if re.fullmatch(r"\d{3,20}", candidate):
                video_id = candidate

        if not video_id:
            return None

        embed_url = f"https://player.vimeo.com/video/{video_id}"
        return (
            "\n<div class=\"my-4 w-full\" "
            "style=\"position:relative;padding-bottom:56.25%;height:0;overflow:hidden;\">"
            f"<iframe src=\"{embed_url}\" "
            "title=\"Vimeo video\" frameborder=\"0\" allow=\"autoplay; fullscreen; picture-in-picture\" "
            "allowfullscreen "
            "style=\"position:absolute;top:0;left:0;width:100%;height:100%;\"></iframe>"
            "</div>\n"
        )


class PdfEmbed:
    name = "pdf"

    def render(self, directive: EmbedDirective) -> str | None:
        url = (directive.args or "").strip()
        if not url:
            return None
        if not url.lower().startswith("https://"):
            return None

        # Many sites block being embedded in an iframe (X-Frame-Options/CSP).
        # Proxy via the backend so the iframe is same-origin.
        base = _backend_base_url()
        query = urlencode({"url": url})
        iframe_src = f"{base}/__embed/pdf?{query}"
        safe_url = html.escape(iframe_src, quote=True)
        return (
            "\n<div class=\"my-4 w-full\">"
            f"<iframe src=\"{safe_url}\" title=\"PDF\" "
            "style=\"width:100%;height:600px;border:0;\"></iframe>"
            "</div>\n"
        )


class GenericIFrameEmbed:
    """Best-effort iframe embed for providers that require an embed URL."""

    def __init__(self, name: str, *, title: str, height_px: int = 480):
        self.name = name
        self._title = title
        self._height_px = height_px

    def render(self, directive: EmbedDirective) -> str | None:
        url = (directive.args or "").strip()
        if not url or not url.lower().startswith("https://"):
            return None

        safe_url = html.escape(url, quote=True)
        safe_title = html.escape(self._title, quote=True)
        return (
            "\n<div class=\"my-4 w-full\">"
            f"<iframe src=\"{safe_url}\" title=\"{safe_title}\" "
            f"style=\"width:100%;height:{self._height_px}px;border:0;\"></iframe>"
            "</div>\n"
        )


class GistEmbed:
    name = "gist"

    def render(self, directive: EmbedDirective) -> str | None:
        value = (directive.args or "").strip()
        if not value:
            return None

        # Prefer the official gist embed script via backend static HTML.
        # This matches HackMD/GitHub behavior and avoids markdown parsing issues
        # (e.g. lines starting with `#` becoming headings).
        gist_js = _build_gist_js_url(value)
        if gist_js:
            base = _backend_base_url()
            query = urlencode({"url": gist_js})
            iframe_src = f"{base}/__embed/gist?{query}"
            return (
                "\n<div class=\"my-4 w-full\">"
                "<iframe sandbox=\"allow-scripts allow-same-origin\" "
                "style=\"width:100%;height:600px;border:0;\" "
                f"src=\"{html.escape(iframe_src, quote=True)}\"></iframe>"
                "</div>\n"
            )

        # Fallback: server-side rendering via GitHub API (no iframe).
        gist_id = _extract_gist_id(value)
        if gist_id:
            rendered = _fetch_gist_html(gist_id)
            if rendered:
                return "\n" + rendered + "\n"

        # Last resort: link only.
        safe_value = html.escape(value, quote=True)
        return (
            "\n<div class=\"my-4\">"
            f"<a href=\"{safe_value}\" target=\"_blank\" rel=\"noreferrer\">"
            f"Gist {html.escape(value)}"
            "</a></div>\n"
        )


def register_backend_embed_routes(app: rx.App) -> None:
    """Register backend (port 8000) embed endpoints.

    These return static HTML so third-party scripts like GitHub Gist (document.write)
    execute reliably when loaded in an iframe.
    """

    def _embed_html(body: str) -> str:
        return (
            "<!doctype html><html><head><meta charset='utf-8'/>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
            "<style>body{margin:0;padding:0;font-family:sans-serif}</style>"
            "</head><body>"
            f"{body}"
            "</body></html>"
        )

    def _get_code(request: StarletteRequest) -> str:
        """Read code from query params.

        Prefer `b64` to avoid URL-encoding issues for multi-line blocks.
        """

        b64 = (request.query_params.get("b64") or "").strip()
        if b64:
            try:
                padded = b64 + "=" * (-len(b64) % 4)
                return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError):
                return ""
        return (request.query_params.get("code") or "").strip()

    def _api_embed_gist(request: StarletteRequest) -> HTMLResponse:
        url = (request.query_params.get("url") or "").strip()
        if not url or not url.lower().startswith("https://"):
            return HTMLResponse(_embed_html("<pre>Invalid gist URL</pre>"))

        safe = (
            url.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
        body = (
            "<style>body{margin:0;padding:0} .gist{font-size:12px}</style>"
            f"<script src='{safe}'></script>"
        )
        return HTMLResponse(_embed_html(body))

    def _api_embed_sequence(request: StarletteRequest) -> HTMLResponse:
        code = _get_code(request)
        if not code:
            return HTMLResponse(_embed_html("<pre>(empty)</pre>"))

        safe_code = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        body = (
            "<div id='diagram'></div>"
            f"<pre id='source' style='display:none'>{safe_code}</pre>"
            "<script src='https://bramp.github.io/js-sequence-diagrams/js/webfont.js'></script>"
            "<script src='https://bramp.github.io/js-sequence-diagrams/js/snap.svg-min.js'></script>"
            "<script src='https://bramp.github.io/js-sequence-diagrams/js/underscore-min.js'></script>"
            "<script src='https://bramp.github.io/js-sequence-diagrams/js/sequence-diagram-min.js'></script>"
            "<script>(function(){try{var text=document.getElementById('source').textContent;"
            "var d=Diagram.parse(text);d.drawSVG('diagram',{theme:'simple'});}catch(e){"
            "var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);}})();</script>"
        )
        return HTMLResponse(_embed_html(body))

    def _api_embed_flow(request: StarletteRequest) -> HTMLResponse:
        code = _get_code(request)
        if not code:
            return HTMLResponse(_embed_html("<pre>(empty)</pre>"))

        safe_code = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        body = (
            "<style>#diagram svg{max-width:100%;height:auto}</style>"
            "<div id='diagram'></div>"
            f"<pre id='source' style='display:none'>{safe_code}</pre>"
            "<script src='https://cdnjs.cloudflare.com/ajax/libs/raphael/2.3.0/raphael.min.js'></script>"
            "<script src='https://cdnjs.cloudflare.com/ajax/libs/flowchart/1.17.1/flowchart.min.js'></script>"
            "<script>(function(){var text=document.getElementById('source').textContent;"
            "try{var diagram=flowchart.parse(text);diagram.drawSVG('diagram');}"
            "catch(e){var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);}})();</script>"
        )
        return HTMLResponse(_embed_html(body))

    def _api_embed_graphviz(request: StarletteRequest) -> HTMLResponse:
        code = _get_code(request)
        if not code:
            return HTMLResponse(_embed_html("<pre>(empty)</pre>"))

        safe_code = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        body = (
            "<style>#diagram svg{max-width:100%;height:auto}</style>"
            "<div id='diagram'></div>"
            f"<pre id='source' style='display:none'>{safe_code}</pre>"
            "<script src='https://cdn.jsdelivr.net/npm/viz.js@2.1.2/viz.js'></script>"
            "<script src='https://cdn.jsdelivr.net/npm/viz.js@2.1.2/full.render.js'></script>"
            "<script>(function(){var text=document.getElementById('source').textContent;"
            "var container=document.getElementById('diagram');"
            "try{var viz=new Viz();viz.renderSVGElement(text).then(function(el){container.appendChild(el);})"
            ".catch(function(){var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);});}"
            "catch(e){var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);}})();</script>"
        )
        return HTMLResponse(_embed_html(body))

    def _api_embed_mermaid(request: StarletteRequest) -> HTMLResponse:
        code = _get_code(request)
        if not code:
            return HTMLResponse(_embed_html("<pre>(empty)</pre>"))

        safe_code = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        body = (
            "<style>#diagram svg{max-width:100%;height:auto}</style>"
            "<div id='diagram' class='mermaid'></div>"
            f"<pre id='source' style='display:none'>{safe_code}</pre>"
            "<script src='https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'></script>"
            "<script>(function(){var el=document.getElementById('diagram');"
            "el.textContent=document.getElementById('source').textContent;"
            "try{mermaid.initialize({startOnLoad:false});mermaid.init(undefined, el);}"
            "catch(e){var pre=document.createElement('pre');pre.textContent=el.textContent;document.body.appendChild(pre);}})();</script>"
        )
        return HTMLResponse(_embed_html(body))

    def _api_embed_abc(request: StarletteRequest) -> HTMLResponse:
        code = _get_code(request)
        if not code:
            return HTMLResponse(_embed_html("<pre>(empty)</pre>"))

        safe_code = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        body = (
            "<style>#paper svg{max-width:100%;height:auto}</style>"
            "<div id='paper'></div>"
            f"<pre id='source' style='display:none'>{safe_code}</pre>"
            "<script src='https://cdn.jsdelivr.net/npm/abcjs@6.2.3/dist/abcjs-basic-min.js'></script>"
            "<script>(function(){var text=document.getElementById('source').textContent;"
            "try{ABCJS.renderAbc('paper', text, {responsive:'resize'});}"
            "catch(e){var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);}})();</script>"
        )
        return HTMLResponse(_embed_html(body))

    def _api_embed_vega(request: StarletteRequest) -> HTMLResponse:
        code = _get_code(request)
        if not code:
            return HTMLResponse(_embed_html("<pre>(empty)</pre>"))

        safe_code = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        body = (
            "<div id='vis'></div>"
            f"<pre id='source' style='display:none'>{safe_code}</pre>"
            "<script src='https://cdn.jsdelivr.net/npm/vega@5/build/vega.min.js'></script>"
            "<script src='https://cdn.jsdelivr.net/npm/vega-lite@5/build/vega-lite.min.js'></script>"
            "<script src='https://cdn.jsdelivr.net/npm/vega-embed@6/build/vega-embed.min.js'></script>"
            "<script>(function(){var text=document.getElementById('source').textContent;"
            "var target=document.getElementById('vis');var spec=null;"
            "try{spec=JSON.parse(text);}catch(e){var pre=document.createElement('pre');pre.textContent='Invalid JSON';document.body.appendChild(pre);return;}"
            "try{vegaEmbed(target, spec, {actions:false}).catch(function(){var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);});}"
            "catch(e){var pre=document.createElement('pre');pre.textContent=text;document.body.appendChild(pre);}})();</script>"
        )
        return HTMLResponse(_embed_html(body))

    def _api_embed_pdf(request: StarletteRequest) -> Response:
        url = (request.query_params.get("url") or "").strip()
        if not url or not url.lower().startswith("https://"):
            return HTMLResponse(_embed_html("<pre>Invalid PDF URL</pre>"))

        try:
            parsed = urlparse(url)
        except Exception:
            return HTMLResponse(_embed_html("<pre>Invalid PDF URL</pre>"))

        host = (parsed.hostname or "").strip()
        if not host:
            return HTMLResponse(_embed_html("<pre>Invalid PDF URL</pre>"))

        # Basic SSRF protections.
        host_l = host.lower()
        if host_l in {"localhost"} or host_l.endswith(".local"):
            return HTMLResponse(_embed_html("<pre>Blocked host</pre>"))

        try:
            ip = ipaddress.ip_address(host)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
            ):
                return HTMLResponse(_embed_html("<pre>Blocked host</pre>"))
        except ValueError:
            # Not an IP literal; allow hostname.
            pass

        # Avoid non-standard ports.
        if parsed.port not in (None, 443):
            return HTMLResponse(_embed_html("<pre>Blocked port</pre>"))

        try:
            req = Request(url, headers={"User-Agent": "codoc-in-md"})
            with urlopen(req, timeout=10) as resp:
                content_type = (resp.headers.get("Content-Type") or "").lower()
                max_bytes = 15 * 1024 * 1024
                chunks: list[bytes] = []
                total = 0
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        return HTMLResponse(_embed_html("<pre>PDF too large</pre>"))
                    chunks.append(chunk)
        except Exception:
            return HTMLResponse(_embed_html("<pre>Failed to fetch PDF</pre>"))

        # Best-effort content-type validation (some servers mislabel PDFs).
        if "application/pdf" not in content_type and not (parsed.path or "").lower().endswith(".pdf"):
            return HTMLResponse(_embed_html("<pre>URL is not a PDF</pre>"))

        data = b"".join(chunks)
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )

    existing_paths = {getattr(r, "path", None) for r in getattr(app._api, "routes", [])}
    if "/__embed/gist" not in existing_paths:
        app._api.add_route("/__embed/gist", _api_embed_gist, methods=["GET"])
    if "/__embed/sequence" not in existing_paths:
        app._api.add_route("/__embed/sequence", _api_embed_sequence, methods=["GET"])
    if "/__embed/flow" not in existing_paths:
        app._api.add_route("/__embed/flow", _api_embed_flow, methods=["GET"])
    if "/__embed/graphviz" not in existing_paths:
        app._api.add_route("/__embed/graphviz", _api_embed_graphviz, methods=["GET"])
    if "/__embed/mermaid" not in existing_paths:
        app._api.add_route("/__embed/mermaid", _api_embed_mermaid, methods=["GET"])
    if "/__embed/abc" not in existing_paths:
        app._api.add_route("/__embed/abc", _api_embed_abc, methods=["GET"])
    if "/__embed/vega" not in existing_paths:
        app._api.add_route("/__embed/vega", _api_embed_vega, methods=["GET"])
    if "/__embed/pdf" not in existing_paths:
        app._api.add_route("/__embed/pdf", _api_embed_pdf, methods=["GET"])


class SlideShareEmbed:
    name = "slideshare"

    def render(self, directive: EmbedDirective) -> str | None:
        value = (directive.args or "").strip()
        if not value:
            return None

        url = value
        if not url.lower().startswith("https://"):
            # HackMD shorthand like `user/slug`.
            url = f"https://www.slideshare.net/{url.lstrip('/')}"

        html_snippet = _fetch_oembed_html(
            endpoint="https://www.slideshare.net/api/oembed/2",
            target_url=url,
        )
        if html_snippet:
            return f"\n<div class=\"my-4 w-full\">{html_snippet}</div>\n"

        # Fallback: try iframing the URL.
        safe_url = html.escape(url, quote=True)
        return (
            "\n<div class=\"my-4 w-full\">"
            f"<iframe src=\"{safe_url}\" title=\"SlideShare\" "
            "style=\"width:100%;height:520px;border:0;\"></iframe>"
            "</div>\n"
        )


class SpeakerDeckEmbed:
    name = "speakerdeck"

    def render(self, directive: EmbedDirective) -> str | None:
        value = (directive.args or "").strip()
        if not value:
            return None

        url = value
        if not url.lower().startswith("https://"):
            url = f"https://speakerdeck.com/{url.lstrip('/')}"

        html_snippet = _fetch_oembed_html(
            endpoint="https://speakerdeck.com/oembed.json",
            target_url=url,
        )
        if html_snippet:
            return f"\n<div class=\"my-4 w-full\">{html_snippet}</div>\n"

        safe_url = html.escape(url, quote=True)
        return (
            "\n<div class=\"my-4 w-full\">"
            f"<iframe src=\"{safe_url}\" title=\"SpeakerDeck\" "
            "style=\"width:100%;height:520px;border:0;\"></iframe>"
            "</div>\n"
        )


class SequenceDiagramBlock:
    language = "sequence"

    def render(self, block: FencedCodeBlock) -> str | None:
        # Prefer using a first-party endpoint for rendering, because markdown sanitizers
        # often strip iframe[srcdoc].
        base = _backend_base_url()
        query = urlencode({"b64": _encode_code_b64(block.code)})
        iframe_src = f"{base}/__embed/sequence?{query}"
        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:360px;border:0;\" "
            f"src=\"{html.escape(iframe_src, quote=True)}\"></iframe>"
            "</div>\n"
        )


class FlowChartBlock:
    language = "flow"

    def render(self, block: FencedCodeBlock) -> str | None:
        base = _backend_base_url()
        query = urlencode({"b64": _encode_code_b64(block.code)})
        iframe_src = f"{base}/__embed/flow?{query}"
        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:420px;border:0;\" "
            f"src=\"{html.escape(iframe_src, quote=True)}\"></iframe>"
            "</div>\n"
        )


class GraphvizBlock:
    language = "graphviz"

    def render(self, block: FencedCodeBlock) -> str | None:
        base = _backend_base_url()
        query = urlencode({"b64": _encode_code_b64(block.code)})
        iframe_src = f"{base}/__embed/graphviz?{query}"
        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:420px;border:0;\" "
            f"src=\"{html.escape(iframe_src, quote=True)}\"></iframe>"
            "</div>\n"
        )


class MermaidBlock:
    language = "mermaid"

    def render(self, block: FencedCodeBlock) -> str | None:
        base = _backend_base_url()
        query = urlencode({"b64": _encode_code_b64(block.code)})
        iframe_src = f"{base}/__embed/mermaid?{query}"
        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:420px;border:0;\" "
            f"src=\"{html.escape(iframe_src, quote=True)}\"></iframe>"
            "</div>\n"
        )


class AbcBlock:
    language = "abc"

    def render(self, block: FencedCodeBlock) -> str | None:
        base = _backend_base_url()
        query = urlencode({"b64": _encode_code_b64(block.code)})
        iframe_src = f"{base}/__embed/abc?{query}"
        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:420px;border:0;\" "
            f"src=\"{html.escape(iframe_src, quote=True)}\"></iframe>"
            "</div>\n"
        )


class VegaLiteBlock:
    language = "vega"

    def render(self, block: FencedCodeBlock) -> str | None:
        base = _backend_base_url()
        query = urlencode({"b64": _encode_code_b64(block.code)})
        iframe_src = f"{base}/__embed/vega?{query}"
        return (
            "\n<div class=\"my-4 w-full\">"
            "<iframe sandbox=\"allow-scripts allow-same-origin\" "
            "style=\"width:100%;height:520px;border:0;\" "
            f"src=\"{html.escape(iframe_src, quote=True)}\"></iframe>"
            "</div>\n"
        )


EMBED_EXTENSIONS: dict[str, EmbedExtension] = {
    "youtube": YouTubeEmbed(),
    "vimeo": VimeoEmbed(),
    "gist": GistEmbed(),
    "slideshare": SlideShareEmbed(),
    "speakerdeck": SpeakerDeckEmbed(),
    "pdf": PdfEmbed(),
}


FENCED_BLOCK_EXTENSIONS: dict[str, FencedBlockExtension] = {
    "sequence": SequenceDiagramBlock(),
    "flow": FlowChartBlock(),
    "flowchart": FlowChartBlock(),
    "graphviz": GraphvizBlock(),
    "dot": GraphvizBlock(),
    "mermaid": MermaidBlock(),
    "abc": AbcBlock(),
    "vega": VegaLiteBlock(),
    "vega-lite": VegaLiteBlock(),
}


def apply_hackmd_embeds(markdown_text: str, *, extensions: dict[str, EmbedExtension] | None = None) -> str:
    """Convert HackMD-like extensions into raw HTML blocks.

    Unknown directives are left unchanged.

    Args:
        markdown_text: Source markdown.
        extensions: Optional mapping overriding EMBED_EXTENSIONS.
    """

    directive_registry = extensions or EMBED_EXTENSIONS
    text = markdown_text or ""

    def _replace_directives(segment: str) -> str:
        def _replace(match: re.Match) -> str:
            raw = match.group(0)
            name = (match.group("name") or "").strip().lower()
            args = (match.group("args") or "").strip()
            ext = directive_registry.get(name)
            if not ext:
                return raw

            rendered = ext.render(EmbedDirective(name=name, args=args, raw=raw))
            return rendered if rendered is not None else raw

        return _DIRECTIVE_RE.sub(_replace, segment)

    out_parts: list[str] = []

    fence_open_re = re.compile(r"^(?P<indent>\s{0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
    lines = text.splitlines(keepends=True)
    i = 0
    buf: list[str] = []

    def _flush_buf():
        if not buf:
            return
        out_parts.append(_replace_directives("".join(buf)))
        buf.clear()

    while i < len(lines):
        line = lines[i].rstrip("\r\n")
        m_open = fence_open_re.match(line)
        if not m_open:
            buf.append(lines[i])
            i += 1
            continue

        _flush_buf()

        indent = m_open.group("indent")
        fence = m_open.group("fence")
        info = (m_open.group("info") or "").strip()
        fence_char = fence[0]
        fence_len = len(fence)
        close_re = re.compile(rf"^{re.escape(indent)}{re.escape(fence_char)}{{{fence_len},}}\s*$")

        j = i + 1
        body_lines: list[str] = []
        while j < len(lines) and not close_re.match(lines[j].rstrip("\r\n")):
            body_lines.append(lines[j])
            j += 1

        if j >= len(lines):
            # Unclosed fence: treat as literal text.
            buf.append(lines[i])
            buf.extend(body_lines)
            break

        raw = "".join([lines[i], *body_lines, lines[j]])

        token = (info.split(None, 1)[0] if info else "").strip()
        # HackMD-style options live on the first token: lang=101, lang=+, lang!
        if token.endswith("!"):
            token = token[:-1]
        if "=" in token:
            token = token.split("=", 1)[0]
        lang = token.strip().lower()

        code = "".join(body_lines)
        # Match old behavior: fenced body excludes the newline right before the closing fence.
        if code.endswith("\n"):
            code = code[:-1]
            if code.endswith("\r"):
                code = code[:-1]

        block_ext = FENCED_BLOCK_EXTENSIONS.get(lang)
        if block_ext:
            rendered = block_ext.render(FencedCodeBlock(language=lang, code=code, raw=raw))
            out_parts.append(rendered if rendered is not None else raw)
        else:
            out_parts.append(raw)

        i = j + 1

    _flush_buf()
    return "".join(out_parts)
