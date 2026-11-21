"""What a registered email address may look like: exactly one plain mailbox, nothing a mail header could misread."""
import pytest

from services.email_address import clean_email, email_problem, optional_email

VALID = ["a@example.com", "First.Last@Example.COM", "o'brien+tag@sub.example.co.uk", "a_b-c@ex-ample.org", "x@y.pk",
         "  padded@example.com  ", "1234@example.test"]
INVALID = ["", "   ", "plain", "a@b", "a@b.", "a@.com", "a@b..com", "a..b@example.com", ".a@example.com", "a.@example.com",
           "a@@example.com", "a@b@example.com", "a b@example.com", "a@exa mple.com", "a,b@example.com", "a@example.com,b@example.com",
           "a@example.com;b@example.com", "a@example.com b@example.com", "<a@example.com>", "Name <a@example.com>",
           '"a"@example.com', "(c)a@example.com", "a@[127.0.0.1]", "a@127.0.0.1", "a\b@example.com", "a:b@example.com",
           "a@example.com\nBcc: x@y.com", "a@example.com\r\nBcc: x@y.com", "a@example.com\n", "\na@example.com", "a\x00@example.com",
           "a@exa\tmple.com", "é@example.com", "a@exämple.com", "a@-example.com", "a@example-.com", "a@example.c",
           "a@example.123", "x" * 65 + "@example.com", "a@" + "b" * 64 + ".com", "a@" + ("b." * 130) + "com", None, 5, ["a@b.com"]]


@pytest.mark.parametrize("address", VALID)
def test_valid_addresses_are_accepted_and_lowercased(address):
    assert email_problem(address) is None
    assert clean_email(address) == address.strip().lower()


@pytest.mark.parametrize("address", INVALID)
def test_everything_else_is_refused(address):
    assert email_problem(address) is not None
    with pytest.raises(ValueError):
        clean_email(address)


def test_an_optional_field_may_be_left_blank_but_not_filled_wrongly():
    assert optional_email(None) is None and optional_email("   ") is None
    assert optional_email(" Ok@Example.com ") == "ok@example.com"
    for bad in ("\n", "a,b@example.com", "a@example.com\nBcc: x@y.com"):
        with pytest.raises(ValueError):
            optional_email(bad)
