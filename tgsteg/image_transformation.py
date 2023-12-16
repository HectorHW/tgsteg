import io
import typing
from PIL import Image
import itertools

from tgsteg.data_encoding import decode_string, encode_string
from tgsteg.pixel_enumeration import PixelEnumerator, Edges
from tgsteg import data_encoding


def extract_image(data: io.BytesIO) -> Image.Image:
    return Image.open(data)


def compress_image(data: Image.Image) -> io.BytesIO:
    result = io.BytesIO()
    data.save(result, format="jpeg", quality=87)
    return result


def bake(
    image: Image.Image,
    data: list[bool],
    pixel_strategy: typing.Type[PixelEnumerator],
) -> Image.Image:
    if len(data) > data_encoding.DATA_LIMIT:
        raise ValueError(
            f"data is too big for container of size {data_encoding.DATA_LIMIT} ({data_encoding.MAX_LETTERS} letters)"
        )

    bits = data_encoding.pack_bits(data)

    pixelaccess = image.load()
    strategy = pixel_strategy(image.size)

    for bit in bits:
        try:
            position = next(strategy)
        except StopIteration as e:
            raise ValueError("data too big for provided image and strategy") from e

        pixelaccess[position] = (255, 255, 255) if bit else (0, 0, 0)

    return image


def unbake(
    image: Image.Image,
    pixel_strategy: typing.Type[PixelEnumerator],
) -> list[bool]:
    pixels = image.load()

    strategy = pixel_strategy(image.size)

    bits = [
        transmute_pixel(pixels[position])
        for position in itertools.islice(strategy, data_encoding.TOTAL_BITS)
    ]

    return list(data_encoding.unpack_bits(bits))


def transmute_pixel(pixel: tuple[int, int, int]) -> bool:
    return sum(pixel) > 255 * 3 / 2


def bake_string(image: Image.Image, value: str) -> Image.Image:
    data = encode_string(value)
    return bake(image, data, Edges)


def unbake_string(image: Image.Image) -> str:
    bits = unbake(image, Edges)
    return decode_string(bits)


if __name__ == "__main__":
    image = Image.open("image.jpg")
    baked = bake_string(image, "lt_three")
    baked.save("output.jpg", quality=87)

    del baked, image

    image = Image.open("output.jpg")
    raw = unbake_string(image)
    print(raw)
