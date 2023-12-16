import io
from PIL import Image

from tgsteg.data_encoding import decode_int, decode_string, encode_int, encode_string


def extract_image(data: io.BytesIO) -> Image.Image:
    return Image.open(data)


def compress_image(data: Image.Image) -> io.BytesIO:
    result = io.BytesIO()
    data.save(result, format="jpeg", quality=87)
    return result


MAGIC = [True, False, False, True, False, True]
LEN_PREFIX = 6


class IncorrectMagic(ValueError):
    pass


def bake(image: Image.Image, data: list[bool]) -> Image.Image:
    if len(data) > 2**LEN_PREFIX - 1:
        raise ValueError(f"data is too big for length prefix of {LEN_PREFIX}")

    if image.size[0] < LEN_PREFIX + len(data):
        raise ValueError("passed data is too long for provided image base")

    bits = MAGIC + encode_int(len(data), LEN_PREFIX) + data

    pixelaccess = image.load()

    for i, bit in enumerate(bits):
        pixelaccess[i, 0] = (255, 255, 255) if bit else (0, 0, 0)

    return image


def unbake(image: Image.Image) -> list[bool]:
    pixels = image.load()
    interesting_pixels = [pixels[i, 0] for i in range(image.size[0])]
    bits = [transmute_pixel(px) for px in interesting_pixels]
    if len(bits) < len(MAGIC) + LEN_PREFIX:
        raise ValueError("amount of bits parsed from image is too low")

    if bits[: len(MAGIC)] != MAGIC:
        raise IncorrectMagic("magic value does not match")

    bits = bits[len(MAGIC) :]

    size, data = decode_int(bits[:LEN_PREFIX]), bits[LEN_PREFIX:]
    if size > len(data):
        raise ValueError("embedded size value is too big for provided data")

    return data[:size]


def transmute_pixel(pixel: tuple[int, int, int]) -> bool:
    return sum(pixel) > 255 * 3 / 2


def bake_string(image: Image.Image, data: str) -> Image.Image:
    return bake(image, encode_string(data))


def unbake_string(image: Image.Image) -> str:
    raw = unbake(image)
    return decode_string(raw)


if __name__ == "__main__":
    image = Image.open("image.jpg")
    baked = bake(image, encode_string("lt_three"))
    baked.save("output.jpg", quality=87)

    del baked, image

    image = Image.open("output.jpg")
    raw = unbake(image)
    assert raw is not None
    print(decode_string(raw))
