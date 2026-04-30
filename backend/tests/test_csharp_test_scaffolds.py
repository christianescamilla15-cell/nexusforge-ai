"""Tests for the C# test-scaffold generators (T5 #2 — 2026-04-30).

The two generators (`refactor/cicd_generator.py` and
`refactor/test_generator.py`) used to emit:

    [Fact]
    public void Foo_ShouldReturnExpectedResult()
    {
        Assert.True(true); // TODO: implement
    }

That made every generated scaffold appear in xUnit's runner output
as a passing test, falsely inflating the green count and hiding
the fact that no real assertion existed. Both now emit
`[Fact(Skip = "scaffold: ...")]` so the runner correctly reports
the test as Skipped — making it obvious the assertion is still
TODO.
"""
from __future__ import annotations


# ─── cicd_generator.generate_csharp_tests (used by /api/refactor/generate-cicd) ──


def test_cicd_generator_marks_tests_as_skipped_not_passing():
    """The generator's xUnit output must NOT contain bare
    `[Fact]` + `Assert.True(true)`. Both should be replaced by
    `[Fact(Skip = "...")]` with no body assertion."""
    from app.refactor.cicd_generator import generate_xunit_test_class

    output = generate_xunit_test_class(
        class_name="ExampleService",
        methods=[
            {"name": "DoThing", "return_type": "int", "params": 1},
            {"name": "ComputeNoArgs", "return_type": "void", "params": 0},
        ],
        namespace="Example.Tests",
    )

    # Skipped, not silently passing.
    assert "Skip = " in output
    assert 'Skip = "scaffold' in output  # the convention
    # The old false-positive pattern is gone.
    assert "Assert.True(true)" not in output


def test_cicd_generator_emits_skip_for_each_method():
    """Both the happy-path AND the null-input scaffold should be
    skipped — neither is a real test until a human implements it."""
    from app.refactor.cicd_generator import generate_xunit_test_class

    output = generate_xunit_test_class(
        class_name="X",
        methods=[{"name": "Foo", "return_type": "string", "params": 2}],
        namespace="Y",
    )

    # 1 happy-path scaffold + 1 null-input scaffold (params > 0) → 2 skips.
    assert output.count("Skip = ") == 2


def test_cicd_generator_skip_message_names_the_method():
    """The skip reason should mention the source method so an engineer
    scanning runner output knows which scaffold to flesh out."""
    from app.refactor.cicd_generator import generate_xunit_test_class

    output = generate_xunit_test_class(
        class_name="X",
        methods=[{"name": "ParseInput", "return_type": "int", "params": 1}],
        namespace="Y",
    )

    assert "ParseInput" in output
    # Skip message must include the method name (per the
    # f"scaffold: ... for {name}" convention).
    assert "for ParseInput" in output


# ─── test_generator._generate_csharp_tests (used by scan-multilang) ──────


def test_test_generator_csharp_uses_skip_attribute():
    """The non-CICD test_generator path also produces xUnit
    scaffolds. Pin the same convention."""
    from app.refactor.test_generator import _generate_csharp_tests

    out = _generate_csharp_tests(
        source_file="ExampleService.cs",
        funcs=[
            {"name": "Add", "return_type": "int"},
            {"name": "Subtract", "return_type": "int"},
        ],
        imports=[],
    )

    assert "[Fact(Skip = " in out
    assert "Assert.True(true)" not in out


def test_test_generator_csharp_includes_method_name_in_skip_reason():
    from app.refactor.test_generator import _generate_csharp_tests

    out = _generate_csharp_tests(
        source_file="X.cs",
        funcs=[{"name": "Multiply", "return_type": "int"}],
        imports=[],
    )

    assert "Multiply" in out
    assert "for Multiply" in out  # skip-message convention
