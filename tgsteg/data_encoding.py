from collections.abc import Sequence
import dataclasses
import string
import math
import typing
import bchlib  # type: ignore[import-not-found]

UnencodedBits = typing.NewType("UnencodedBits", Sequence[bool])
EncodedBits = typing.NewType("EncodedBits", Sequence[bool])

ALPHABET: str = string.ascii_lowercase + string.digits + "-" + "_" + "@" + ":" + " "

BITS_REQUIRED = math.ceil(math.log2(len(ALPHABET)))


def encode_int(value: int, bitsize: int = BITS_REQUIRED) -> list[bool]:
    if value >= 2**bitsize - 1:
        raise ValueError("data is too big for specified bitsize")

    binary_repr = [letter == "1" for letter in f"{value:b}"]

    return [False] * (bitsize - len(binary_repr)) + binary_repr


def decode_int(value: Sequence[bool]) -> int:
    return int("".join({True: "1", False: "0"}[item] for item in value), 2)


def string_to_packed_numbers(value: str) -> list[int]:
    return [ALPHABET.index(letter) for letter in value]


class StringMagicMismatch(ValueError):
    pass


MAGIC = [True, False, False, True, False, True]


def string_to_bits(data: str, magic: list[bool] = MAGIC) -> UnencodedBits:
    result = []
    for digit in string_to_packed_numbers(data):
        result += encode_int(digit)

    return UnencodedBits(list(magic) + result)


def can_fit(value: str | UnencodedBits) -> bool:
    if isinstance(value, str):
        return can_fit(string_to_bits(value))

    return len(value) < DATA_LIMIT


def string_from_bits(data: UnencodedBits, magic: list[bool] = MAGIC) -> str:
    if len(data) < len(magic) or data[: len(magic)] != magic:
        raise StringMagicMismatch("got magic mismatch while decoding")

    data = UnencodedBits(data[len(magic) :])

    if len(data) % BITS_REQUIRED != 0:
        raise ValueError("incorrect amount of data passed")

    result = []

    for offset in range(0, len(data), BITS_REQUIRED):
        slice = data[offset : offset + BITS_REQUIRED]
        digit = decode_int(slice)
        if digit >= len(ALPHABET):
            raise ValueError("value outside of code range")
        result.append(ALPHABET[digit])

    return "".join(result)


LEN_PREFIX: int = 6
DATA_LIMIT: int = 2**LEN_PREFIX - 1
MAX_LETTERS: int = DATA_LIMIT // BITS_REQUIRED
CONTAINER_SIZE: int = 8 * math.ceil((LEN_PREFIX + DATA_LIMIT) / 8)


@dataclasses.dataclass
class LengthPrefixedBits(Sequence[bool]):
    data: Sequence[bool]
    prefix_size: int = LEN_PREFIX

    @classmethod
    def encode(
        cls,
        bits: Sequence[bool],
        prefix_size: int = LEN_PREFIX,
        container_size: int = CONTAINER_SIZE,
    ) -> typing.Self:
        prefix = encode_int(len(bits), prefix_size)
        pad = [False] * (container_size - len(prefix) - len(bits))
        return cls(data=prefix + list(bits) + pad, prefix_size=prefix_size)

    def decode(self, prefix_size: int = LEN_PREFIX) -> Sequence[bool]:
        size, tail = decode_int(self.data[:prefix_size]), self.data[prefix_size:]
        return tail[:size]

    def __len__(self) -> int:
        return decode_int(self.data[: self.prefix_size])

    @typing.overload
    def __getitem__(self, idx: int, /) -> bool:
        ...

    @typing.overload
    def __getitem__(self, idx: slice, /) -> Sequence[bool]:
        ...

    def __getitem__(self, idx: int | slice, /) -> bool | Sequence[bool]:
        return self.data[: self.prefix_size][idx]


def bits_to_bytes(data: Sequence[bool]) -> Sequence[int]:
    if len(data) % 8 != 0:
        raise ValueError("incorrect amount of bits")

    result = []

    for offset in range(0, len(data), 8):
        window = data[offset : offset + 8]
        result.append(decode_int(window))

    return result


def bytes_to_bits(data: Sequence[int]) -> Sequence[bool]:
    result = []
    for byte in data:
        result += encode_int(byte, 8)
    return result


REDUNDANCY = 30e-2

REDUNDANCY_BYTES = math.ceil(CONTAINER_SIZE * REDUNDANCY / 8)

TOTAL_BITS = REDUNDANCY_BYTES * 8 + CONTAINER_SIZE


@dataclasses.dataclass
class BCHEncoded:
    data: Sequence[int]

    @staticmethod
    def get_encoder() -> typing.Any:
        bch = bchlib.BCH(t=REDUNDANCY_BYTES, m=8)
        max_data_len = bch.n // 8 - (bch.ecc_bits + 7) // 8
        bch.data_len = max_data_len
        return bch

    @classmethod
    def encode(cls, original_data: Sequence[int]) -> typing.Self:
        bch = cls.get_encoder()
        ecc = bch.encode(bytes(original_data))
        return cls(data=list(ecc) + list(original_data))

    def decode(self) -> Sequence[int]:
        buffer = bytearray(self.data)
        data, ecc = buffer[REDUNDANCY_BYTES:], buffer[:REDUNDANCY_BYTES]
        bch = self.get_encoder()
        bch.correct(data, ecc)
        return list(data)


def pack_bits(data: UnencodedBits) -> EncodedBits:
    length_prefixed = LengthPrefixedBits.encode(data)
    lp_bytes = bits_to_bytes(length_prefixed.data)
    bytes_with_redundancy = BCHEncoded.encode(lp_bytes)
    return EncodedBits(bytes_to_bits(bytes_with_redundancy.data))


def unpack_bits(code: EncodedBits) -> UnencodedBits:
    redundant_bytes = bits_to_bytes(code)
    decoded_bytes = BCHEncoded(redundant_bytes).decode()
    bits = bytes_to_bits(decoded_bytes)
    return UnencodedBits(LengthPrefixedBits(bits).decode())


def pack_string(value: str) -> EncodedBits:
    encoded = string_to_bits(value, MAGIC)
    return pack_bits(encoded)


def unpack_string(bits: EncodedBits) -> str:
    unpacked_and_fixed = unpack_bits(bits)
    return string_from_bits(unpacked_and_fixed, MAGIC)
