# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""The sources must run on Python 3.10, the oldest version the README names.

Python 3.12 lets an f-string reuse its own quote character inside a
replacement field; 3.10 and 3.11 reject that with a SyntaxError.  On 3.12 and
later the tokenizer shows the nesting, so the first test finds such f-strings
without an old interpreter.  Run under 3.10, the second test is the check.
"""
import glob
import os
import sys
import tokenize

import pytest

from conftest import REPO

SOURCES = sorted(glob.glob(os.path.join(REPO, "*.py")))


def _quote(token_text):
    body = token_text.lstrip("rRbBuUfF")
    return body[:3] if body[:3] in ('"""', "'''") else body[:1]


@pytest.mark.skipif(sys.version_info < (3, 12), reason="older tokenizers cannot read the lines in question")
@pytest.mark.parametrize("path", SOURCES, ids=os.path.basename)
def test_no_fstring_reuses_its_quote(path):
    enclosing, reused = [], []
    with open(path, "rb") as f:
        for tok in tokenize.tokenize(f.readline):
            if tok.type == tokenize.FSTRING_START:
                if _quote(tok.string) in enclosing:
                    reused.append(tok.start[0])
                enclosing.append(_quote(tok.string))
            elif tok.type == tokenize.FSTRING_END:
                enclosing.pop()
            elif tok.type == tokenize.STRING and enclosing and _quote(tok.string) in enclosing:
                reused.append(tok.start[0])
    assert not reused, f"f-string reuses its quote (needs Python 3.12) at lines {reused}"


@pytest.mark.parametrize("path", SOURCES, ids=os.path.basename)
def test_source_compiles_on_this_python(path):
    with open(path, encoding="utf-8") as f:
        compile(f.read(), path, "exec")
