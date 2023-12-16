from collections.abc import Sequence
from tgsteg import data_encoding
import pytest


@pytest.fixture
def original_message() -> Sequence[int]:
    bits = data_encoding.LengthPrefixedBits.encode([True, False, False])
    return data_encoding.bits_to_bytes(bits.data)


def test_message_is_encoded_with_bch(original_message: Sequence[int]) -> None:
    data_encoding.BCHEncoded.encode(original_message)


@pytest.fixture
def code(original_message: Sequence[int]) -> data_encoding.BCHEncoded:
    return data_encoding.BCHEncoded.encode(original_message)


def test_message_is_decoded_correctly(
    code: data_encoding.BCHEncoded, original_message: Sequence[int]
) -> None:
    assert code.decode() == original_message


@pytest.fixture
def original_text() -> str:
    return "lt_three"


@pytest.fixture
def packed_bits(original_text: str) -> Sequence[bool]:
    return data_encoding.pack_string(original_text)


def test_bits_are_unpacked(original_text: str, packed_bits: Sequence[bool]) -> None:
    assert data_encoding.unpack_string(packed_bits) == original_text
