"""Values of stores built from short-circuit and conditional expressions (STATUS, 2026-11-18).

The extractor reads bytecode in a line; the two paths of `a or b` or `x if c else y` meet at a
jump target, and the value there must be the whole expression or `…`, never one half.
"""

from ableton_remote_script_mcp.extractor import function_statements, read_code


def stores(body: str) -> dict[str, str]:
    src = "def f(self, ok, a, b, c, x, y):\n" + "".join(f"    {line}\n" for line in body.splitlines())
    code = compile(src, "m.py", "exec").co_consts[0]
    return {st["store"]: st["value"] for st in function_statements(code) if "store" in st}


def test_or_and_and_keep_both_sides():
    got = stores("self.p = a.mute or a.muted_via_solo\nself.q = a and b\nself.r = a or b or c")
    assert got == {"self.p": "a.mute or a.muted_via_solo", "self.q": "a and b", "self.r": "a or b or c"}


def test_conditional_expression_is_not_one_branch():
    got = stores("self.p = x if ok else y\nself.q = b")
    assert got["self.p"] in ("…", "x if ok else y") and got["self.q"] == "b"


def test_store_after_an_if_statement_is_unaffected():
    got = stores("if ok:\n    self.p = a\nelse:\n    self.p = b\nself.q = c")
    assert got["self.q"] == "c"


def test_class_attribute_from_a_conditional_expression():
    code = compile("class C:\n    v = 1 if True else 2\n    w = 3\n", "m.py", "exec")
    members = read_code(code, "m", False, "m.py").classes[0].members
    assert members["w"].value == "3"
    assert members["v"].value in ("1", "…") or members["v"].value_literal is False
