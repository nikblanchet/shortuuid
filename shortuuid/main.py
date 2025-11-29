"""Concise UUID generation."""

import math
import secrets
import uuid as _uu
from typing import Final, NewType

# Type alias for encoded short UUIDs
ShortUUIDStr = NewType("ShortUUIDStr", str)

# Default alphabet excludes similar-looking characters (I, O, l, 0)
DEFAULT_ALPHABET: Final = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


class ShortUUIDError(Exception):
    """Base exception for shortuuid."""


class InvalidAlphabetError(ShortUUIDError):
    """Raised when alphabet has fewer than 2 unique characters."""


class InvalidInputError(ShortUUIDError):
    """Raised when encode/decode receives wrong input type."""


def int_to_string(number: int, alphabet: list[str], padding: int | None = None) -> str:
    """Convert a number to a string, using the given alphabet.

    The output has the most significant digit first.
    """
    output = ""
    alpha_len = len(alphabet)
    while number:
        number, digit = divmod(number, alpha_len)
        output += alphabet[digit]
    if padding:
        remainder = max(padding - len(output), 0)
        output = output + alphabet[0] * remainder
    return output[::-1]


def string_to_int(
    string: str,
    alphabet: list[str],
    alphabet_index: dict[str, int] | None = None,
) -> int:
    """Convert a string to a number, using the given alphabet.

    The input is assumed to have the most significant digit first.
    If alphabet_index is provided, uses O(1) dict lookup instead of O(n) list.index().
    """
    if alphabet_index is None:
        alphabet_index = {char: idx for idx, char in enumerate(alphabet)}
    number = 0
    alpha_len = len(alphabet)
    for char in string:
        try:
            number = number * alpha_len + alphabet_index[char]
        except KeyError:
            raise ValueError(f"'{char}' is not in alphabet") from None
    return number


class ShortUUID:
    """Generates concise, URL-safe UUIDs."""

    __slots__ = ("_alphabet", "_alphabet_str", "_alpha_len", "_alphabet_index", "_length")

    def __init__(self, alphabet: str | None = None, *, dont_sort_alphabet: bool = False) -> None:
        if alphabet is None:
            alphabet = DEFAULT_ALPHABET
        self.set_alphabet(alphabet, dont_sort_alphabet=dont_sort_alphabet)

    def __repr__(self) -> str:
        return f"ShortUUID(alphabet={self.get_alphabet()!r})"

    def encode(self, uuid: _uu.UUID, /, pad_length: int | None = None) -> ShortUUIDStr:
        """Encode a UUID into a string (LSB first) according to the alphabet.

        If leftmost (MSB) bits are 0, the string might be shorter.
        """
        if not isinstance(uuid, _uu.UUID):
            raise InvalidInputError("Input `uuid` must be a UUID object.")
        if pad_length is None:
            pad_length = self._length
        return ShortUUIDStr(int_to_string(uuid.int, self._alphabet, padding=pad_length))

    def decode(self, string: ShortUUIDStr, /, *, legacy: bool = False) -> _uu.UUID:
        """Decode a string according to the current alphabet into a UUID.

        Raises InvalidInputError when encountering illegal characters or a too-long string.

        If string too short, fills leftmost (MSB) bits with 0.

        Pass `legacy=True` if your UUID was encoded with a ShortUUID version prior to
        1.0.0.
        """
        if not isinstance(string, str):
            raise InvalidInputError("Input `string` must be a str.")
        if legacy:
            string = ShortUUIDStr(string[::-1])
        return _uu.UUID(int=string_to_int(string, self._alphabet, self._alphabet_index))

    def uuid(self, name: str | None = None, pad_length: int | None = None) -> ShortUUIDStr:
        """Generate and return a UUID.

        If the name parameter is provided, set the namespace to the provided
        name and generate a UUID.
        """
        if pad_length is None:
            pad_length = self._length

        # If no name is given, generate a random UUID.
        if name is None:
            u = _uu.uuid4()
        elif name.lower().startswith(("http://", "https://")):
            u = _uu.uuid5(_uu.NAMESPACE_URL, name)
        else:
            u = _uu.uuid5(_uu.NAMESPACE_DNS, name)
        return self.encode(u, pad_length)

    def random(self, length: int | None = None) -> ShortUUIDStr:
        """Generate and return a cryptographically secure short random string of `length`."""
        if length is None:
            length = self._length
        return ShortUUIDStr("".join(secrets.choice(self._alphabet) for _ in range(length)))

    def get_alphabet(self) -> str:
        """Return the current alphabet used for new UUIDs."""
        return self._alphabet_str

    def set_alphabet(self, alphabet: str, *, dont_sort_alphabet: bool = False) -> None:
        """Set the alphabet to be used for new UUIDs."""
        # Turn the alphabet into a set and sort it to prevent duplicates
        # and ensure reproducibility.
        new_alphabet = list(dict.fromkeys(alphabet)) if dont_sort_alphabet else list(sorted(set(alphabet)))
        if len(new_alphabet) <= 1:
            raise InvalidAlphabetError("Alphabet with more than one unique symbols required.")
        self._alphabet = new_alphabet
        self._alphabet_str = "".join(new_alphabet)
        self._alpha_len = len(self._alphabet)
        self._alphabet_index = {char: idx for idx, char in enumerate(self._alphabet)}
        self._length = int(math.ceil(math.log(2**128, self._alpha_len)))

    def encoded_length(self, num_bytes: int = 16) -> int:
        """Return the string length of the shortened UUID."""
        factor = math.log(256) / math.log(self._alpha_len)
        return int(math.ceil(factor * num_bytes))


# For backwards compatibility
_global_instance = ShortUUID()
encode = _global_instance.encode
decode = _global_instance.decode
uuid = _global_instance.uuid
random = _global_instance.random
get_alphabet = _global_instance.get_alphabet
set_alphabet = _global_instance.set_alphabet
