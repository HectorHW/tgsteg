import io
import typing
from PIL import Image
import itertools

from tgsteg.data_encoding import decode_int, decode_string, encode_int, encode_string
from tgsteg.pixel_enumeration import PixelEnumerator, TopRow, Edges


def extract_image(data: io.BytesIO) -> Image.Image:
    return Image.open(data)


def compress_image(data: Image.Image) -> io.BytesIO:
    result = io.BytesIO()
    data.save(result, format="jpeg", quality=87)
    return result


MAGIC = [True, False, False, True, False, True]
MAGIC_V2 = [True, False, False, False, True, False]
LEN_PREFIX = 6


class IncorrectMagic(ValueError):
    pass


def bake(
    image: Image.Image,
    data: list[bool],
    magic: list[bool],
    pixel_strategy: typing.Type[PixelEnumerator],
) -> Image.Image:
    if len(data) > 2**LEN_PREFIX - 1:
        raise ValueError(f"data is too big for length prefix of {LEN_PREFIX}")

    bits = encode_int(len(data), LEN_PREFIX) + data

    pixelaccess = image.load()
    strategy = pixel_strategy(image.size)

    for i, bit in enumerate(magic):
        pixelaccess[i, 0] = (255, 255, 255) if bit else (0, 0, 0)

    strategy.consume_magic(len(magic))

    for bit in bits:
        try:
            position = next(strategy)
        except StopIteration as e:
            raise ValueError("data too big for provided image and strategy") from e

        pixelaccess[position] = (255, 255, 255) if bit else (0, 0, 0)

    return image


def unbake(
    image: Image.Image,
    magic: list[bool],
    pixel_strategy: typing.Type[PixelEnumerator],
) -> list[bool]:
    pixels = image.load()
    magic_pixels = [transmute_pixel(pixels[i, 0]) for i in range(len(magic))]

    if magic_pixels != magic:
        raise IncorrectMagic

    strategy = pixel_strategy(image.size)
    strategy.consume_magic(len(magic))

    size_code = [
        transmute_pixel(pixels[pos]) for pos in itertools.islice(strategy, LEN_PREFIX)
    ]
    size = decode_int(size_code)

    result = []

    for bit in range(size):
        try:
            position = next(strategy)
        except StopIteration as e:
            raise ValueError("amount of bits parsed from image is too low") from e

        result.append(transmute_pixel(pixels[position]))

    return result


def transmute_pixel(pixel: tuple[int, int, int]) -> bool:
    return sum(pixel) > 255 * 3 / 2


def bake_string_v1(image: Image.Image, data: str) -> Image.Image:
    return bake(image, encode_string(data), MAGIC, TopRow)


def unbake_string_v1(image: Image.Image) -> str:
    raw = unbake(image, MAGIC, TopRow)
    return decode_string(raw)


def bake_string_v2(image: Image.Image, data: str) -> Image.Image:
    return bake(image, encode_string(data), MAGIC_V2, Edges)


def unbake_string_v2(image: Image.Image) -> str:
    raw = unbake(image, MAGIC_V2, Edges)
    return decode_string(raw)


def unbake_string(image: Image.Image) -> str:
    try:
        return unbake_string_v1(image)
    except IncorrectMagic:
        pass
    return unbake_string_v2(image)


if __name__ == "__main__":
    image = Image.open("image.jpg")
    baked = bake_string_v2(image, "lt_three")
    baked.save("output.jpg", quality=87)

    del baked, image

    image = Image.open("output.jpg")
    raw = unbake_string(image)
    print(raw)
