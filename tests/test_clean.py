from src.clean import clean_text


def test_url_sha_mention_ref():
    result = clean_text(
        "see https://x.com/a and @bob fixes #12 at deadbeef1234567"
    )
    assert "<URL>" in result["clean"]
    assert "<USER>" in result["clean"]
    assert "<REF>" in result["clean"]
    assert "<SHA>" in result["clean"]
    assert "http" not in result["clean"]


def test_html_comment_removed():
    assert "secret" not in clean_text("text <!-- secret --> more")["clean"]


def test_code_fence_extracted():
    result = clean_text("before ```java\nint x=1;\n``` after")
    assert result["has_code"]
    assert "int x=1" in result["code"]
    assert "int x=1" not in result["clean"]


def test_stack_extracted():
    result = clean_text("boom\n    at com.foo.Bar.run(Bar.java:12)\nend")
    assert result["has_stack"]
    assert "Bar.java" in result["stack"]
    assert "Bar.java" not in result["clean"]


def test_non_string_safe():
    assert clean_text(None)["clean"] == ""


def test_raw_columns_are_not_overwritten():
    import pandas as pd

    frame = pd.DataFrame(
        {
            "description": ["see https://example.com"],
            "comments": ["original comment"],
        }
    )
    original = frame.copy(deep=True)
    from src.clean import add_clean_columns

    add_clean_columns(frame, "description", "description")
    add_clean_columns(frame, "comments", "comments")
    pd.testing.assert_frame_equal(
        frame[["description", "comments"]], original
    )
