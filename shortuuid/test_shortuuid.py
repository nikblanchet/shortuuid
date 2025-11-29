"""Tests for shortuuid."""

import string
from collections import defaultdict
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from shortuuid import InvalidAlphabetError, InvalidInputError
from shortuuid.cli import cli
from shortuuid.main import ShortUUID, decode, encode, get_alphabet, random, set_alphabet, uuid

# --- Legacy module-level API tests ---


class TestLegacyAPI:
    """Tests for the module-level convenience functions."""

    def test_generation(self):
        assert 20 < len(uuid()) < 24
        assert 20 < len(uuid("http://www.example.com/")) < 24
        assert 20 < len(uuid("HTTP://www.example.com/")) < 24
        assert 20 < len(uuid("example.com/")) < 24

    def test_encoding(self):
        u = UUID("{3b1f8b40-222c-4a6e-b77e-779d5a94e21c}")
        assert encode(u) == "CXc85b4rqinB7s5J52TRYb"

    def test_decoding(self):
        u = UUID("{3b1f8b40-222c-4a6e-b77e-779d5a94e21c}")
        assert decode("CXc85b4rqinB7s5J52TRYb") == u

    def test_alphabet(self):
        backup_alphabet = get_alphabet()

        alphabet = "01"
        set_alphabet(alphabet)
        assert alphabet == get_alphabet()

        set_alphabet("01010101010101")
        assert alphabet == get_alphabet()

        assert set(uuid()) == set("01")
        assert 116 < len(uuid()) < 140

        u = uuid4()
        assert u == decode(encode(u))

        u = uuid()
        assert u == encode(decode(u))

        with pytest.raises(InvalidAlphabetError):
            set_alphabet("1")
        with pytest.raises(InvalidAlphabetError):
            set_alphabet("1111111")

        set_alphabet(backup_alphabet)

        with pytest.raises(InvalidAlphabetError):
            ShortUUID("0")

    @pytest.mark.parametrize("length", range(1, 100))
    def test_random_length(self, length: int):
        assert len(random(length)) == length

    def test_random_default_length(self):
        assert len(random()) == 22


# --- ShortUUID class tests ---


class TestShortUUID:
    """Tests for the ShortUUID class."""

    def test_generation(self):
        su = ShortUUID()
        assert 20 < len(su.uuid()) < 24
        assert 20 < len(su.uuid("http://www.example.com/")) < 24
        assert 20 < len(su.uuid("HTTP://www.example.com/")) < 24
        assert 20 < len(su.uuid("example.com/")) < 24

    def test_encoding(self):
        su = ShortUUID()
        u = UUID("{3b1f8b40-222c-4a6e-b77e-779d5a94e21c}")
        assert su.encode(u) == "CXc85b4rqinB7s5J52TRYb"

    def test_decoding(self):
        su = ShortUUID()
        u = UUID("{3b1f8b40-222c-4a6e-b77e-779d5a94e21c}")
        assert su.decode("CXc85b4rqinB7s5J52TRYb") == u

    def test_random_consistency(self):
        su = ShortUUID()
        for _ in range(1000):
            assert len(su.random()) == 22

    @pytest.mark.parametrize("length", range(1, 100))
    def test_random_length(self, length: int):
        su = ShortUUID()
        assert len(su.random(length)) == length

    def test_alphabet(self):
        alphabet = "01"
        su1 = ShortUUID(alphabet)
        su2 = ShortUUID()

        assert alphabet == su1.get_alphabet()

        su1.set_alphabet("01010101010101")
        assert alphabet == su1.get_alphabet()

        assert set(su1.uuid()) == set("01")
        assert 116 < len(su1.uuid()) < 140
        assert 20 < len(su2.uuid()) < 24

        u = uuid4()
        assert u == su1.decode(su1.encode(u))

        u = su1.uuid()
        assert u == su1.encode(su1.decode(u))

        with pytest.raises(InvalidAlphabetError):
            su1.set_alphabet("1")
        with pytest.raises(InvalidAlphabetError):
            su1.set_alphabet("1111111")

    def test_unsorted_alphabet(self):
        alphabet = "123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"

        su1 = ShortUUID(alphabet, dont_sort_alphabet=True)
        su2 = ShortUUID()

        assert alphabet == su1.get_alphabet()

        su2.set_alphabet(alphabet, dont_sort_alphabet=True)
        assert alphabet == su2.get_alphabet()

        su2.set_alphabet(alphabet + "123abc", dont_sort_alphabet=True)
        assert alphabet == su2.get_alphabet()

        u = uuid4()
        assert u == su1.decode(su1.encode(u))

        u = su1.uuid()
        assert u == su1.encode(su1.decode(u))

        with pytest.raises(InvalidAlphabetError):
            su1.set_alphabet("1")
        with pytest.raises(InvalidAlphabetError):
            su1.set_alphabet("1111111")

    def test_encoded_length(self):
        su1 = ShortUUID()
        assert su1.encoded_length() == 22

        base64_alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits + "+/"

        su2 = ShortUUID(base64_alphabet)
        assert su2.encoded_length() == 22

        binary_alphabet = "01"
        su3 = ShortUUID(binary_alphabet)
        assert su3.encoded_length() == 128

        su4 = ShortUUID()
        assert su4.encoded_length(num_bytes=8) == 11

    def test_repr(self):
        su = ShortUUID("abc")
        assert repr(su) == "ShortUUID(alphabet='abc')"


# --- Padding tests ---


class TestPadding:
    """Tests for consistent padding behavior."""

    def test_padding_length_consistency(self):
        su = ShortUUID()
        random_uid = uuid4()
        smallest_uid = UUID(int=0)

        encoded_random = su.encode(random_uid)
        encoded_small = su.encode(smallest_uid)

        assert len(encoded_random) == len(encoded_small)

    def test_decode_padded(self):
        su = ShortUUID()
        random_uid = uuid4()
        smallest_uid = UUID(int=0)

        encoded_random = su.encode(random_uid)
        encoded_small = su.encode(smallest_uid)

        assert su.decode(encoded_small) == smallest_uid
        assert su.decode(encoded_random) == random_uid

    def test_roundtrip_consistency(self):
        su = ShortUUID()
        num_iterations = 1000
        uid_lengths: dict[int, int] = defaultdict(int)

        for _ in range(num_iterations):
            random_uid = uuid4()
            encoded_random = su.encode(random_uid)
            uid_lengths[len(encoded_random)] += 1
            decoded_random = su.decode(encoded_random)

            assert random_uid == decoded_random

        assert len(uid_lengths) == 1
        uid_length = next(iter(uid_lengths.keys()))
        assert uid_lengths[uid_length] == num_iterations


# --- Edge case tests ---


class TestEncodingEdgeCases:
    """Tests for encoding edge cases and error handling."""

    @pytest.mark.parametrize("invalid_input", [[], {}, 42, 42.0])
    def test_encode_invalid_input(self, invalid_input):
        su = ShortUUID()
        with pytest.raises(InvalidInputError):
            su.encode(invalid_input)


class TestDecodingEdgeCases:
    """Tests for decoding edge cases and error handling."""

    @pytest.mark.parametrize("invalid_input", [[], {}, (2,), 42, 42.0])
    def test_decode_invalid_input(self, invalid_input):
        su = ShortUUID()
        with pytest.raises(InvalidInputError):
            su.decode(invalid_input)

    def test_decode_invalid_characters(self):
        su = ShortUUID("abc")
        with pytest.raises(ValueError):
            su.decode("xyz")


# --- CLI tests ---


class TestCLI:
    """Tests for the command-line interface."""

    def test_shortuuid_command_produces_uuid(self):
        with patch("shortuuid.cli.print") as mock_print:
            cli([])
            mock_print.assert_called()
            terminal_output = mock_print.call_args[0][0]
            assert len(terminal_output) == 22

    def test_encode_command(self):
        with patch("shortuuid.cli.print") as mock_print:
            cli(["encode", "3b1f8b40-222c-4a6e-b77e-779d5a94e21c"])
            terminal_output = mock_print.call_args[0][0]
            assert terminal_output == "CXc85b4rqinB7s5J52TRYb"

    def test_decode_command(self):
        with patch("shortuuid.cli.print") as mock_print:
            cli(["decode", "CXc85b4rqinB7s5J52TRYb"])
            terminal_output = mock_print.call_args[0][0]
            assert terminal_output == "3b1f8b40-222c-4a6e-b77e-779d5a94e21c"
