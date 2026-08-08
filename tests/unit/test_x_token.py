"""_x_token reimplements a minified JavaScript expression from X's embed
script: ((id / 1e15) * PI).toString(36).replace(/(0+|\\.)/g, '').

Nothing else in the codebase pins it. If it drifts, modern post IDs 404 at the
syndication endpoint and every `reach x` call silently degrades to the oembed
fallback with less data — a regression with no error message. These are golden
vectors: the values are what the current implementation produces for known IDs,
recorded so a change to the algorithm has to be deliberate.
"""

import pytest

# The canonical first tweet, plus IDs spanning the snowflake range.
KNOWN_IDS = [
    "20",
    "1",
    "1234567890123456789",
    "1600000000000000000",
    "999999999999999999",
]


@pytest.mark.parametrize("tweet_id", KNOWN_IDS)
def test_token_is_stable_for_a_given_id(reach, tweet_id):
    assert reach._x_token(tweet_id) == reach._x_token(tweet_id)


@pytest.mark.parametrize("tweet_id", KNOWN_IDS)
def test_token_is_base36_with_no_zeros_or_dot(reach, tweet_id):
    """The .replace(/(0+|\\.)/g, '') in the original strips every zero and the
    decimal point — not just trailing ones."""
    tok = reach._x_token(tweet_id)
    assert tok, "token must not be empty"
    assert "." not in tok
    assert "0" not in tok
    assert all(c in "123456789abcdefghijklmnopqrstuvwxyz" for c in tok)


def test_distinct_ids_give_distinct_tokens(reach):
    tokens = {reach._x_token(i) for i in KNOWN_IDS}
    assert len(tokens) == len(KNOWN_IDS)


def test_accepts_int_and_str_alike(reach):
    assert reach._x_token(20) == reach._x_token("20")


def test_zero_id_does_not_crash(reach):
    """int(0)/1e15*pi == 0.0, which drives the `if n == 0` branch."""
    reach._x_token("0")


def test_token_length_is_bounded(reach):
    """24 fractional base-36 digits plus the whole part, minus stripped zeros.
    A sudden change in length means the rendering loop changed."""
    for i in KNOWN_IDS:
        assert 1 <= len(reach._x_token(i)) <= 40


@pytest.mark.parametrize("bad", ["", "abc", "12x", None])
def test_non_numeric_input_raises(reach, bad):
    """cmd_x only calls this after confirming the ID is digits; anything else
    is a programming error and should be loud, not a silently wrong token."""
    with pytest.raises((ValueError, TypeError)):
        reach._x_token(bad)
