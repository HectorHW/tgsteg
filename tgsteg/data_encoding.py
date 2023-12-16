import string
import math

ALPHABET = string.ascii_lowercase + string.digits + "-" + "_" + "@"

BITS_REQUIRED = math.ceil(math.log2(len(ALPHABET)))


def encode_int(value: int, bitsize: int = BITS_REQUIRED) -> list[bool]:
    if value >= 2**bitsize - 1:
        raise ValueError("data is too big for specified bitsize")

    binary_repr = [letter == "1" for letter in f"{value:b}"]

    return [False] * (bitsize - len(binary_repr)) + binary_repr


def decode_int(value: list[bool]) -> int:
    return int("".join({True: "1", False: "0"}[item] for item in value), 2)


def string_to_packed_numbers(value: str) -> list[int]:
    return [ALPHABET.index(letter) for letter in value]


def encode_string(data: str) -> list[bool]:
    result = []
    for digit in string_to_packed_numbers(data):
        result += encode_int(digit)

    return result


def decode_string(data: list[bool]) -> str:
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
