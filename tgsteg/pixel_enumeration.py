import abc
import collections.abc
import typing


class PixelEnumerator(collections.abc.Iterator[tuple[int, int]]):
    @abc.abstractmethod
    def __init__(self, image_size: tuple[int, int]) -> None:
        ...

    @abc.abstractmethod
    def consume_magic(self, magic_size: int) -> typing.Self:
        ...

    @abc.abstractmethod
    def __next__(self) -> tuple[int, int]:
        ...


class TopRow(PixelEnumerator):
    def __init__(self, image_size: tuple[int, int]) -> None:
        self.row_length = image_size[0]
        self.current = 0

    def consume_magic(self, magic_size: int) -> typing.Self:
        self.current += magic_size
        return self

    def __next__(self) -> tuple[int, int]:
        if self.current == self.row_length:
            raise StopIteration

        self.current += 1

        return (self.current - 1, 0)


class Edges(PixelEnumerator):
    def __init__(self, image_size: tuple[int, int]) -> None:
        self.row_length = image_size[0]
        self.midpoint = image_size[0] // 2
        self.bottom_row = image_size[1] - 1

        self.offsets = [0] * 4

    def consume_magic(self, magic_size: int) -> typing.Self:
        self.offsets[0] += magic_size
        return self

    def __next__(self) -> tuple[int, int]:
        min_idx, min_value = min(enumerate(self.offsets), key=lambda item: item[1])
        if min_value == self.midpoint:
            raise StopIteration
        match min_idx:
            case 0:
                self.offsets[0] += 1
                return (self.offsets[0] - 1, 0)
            case 1:
                self.offsets[1] += 1
                return (self.row_length - self.offsets[1], 0)
            case 2:
                self.offsets[2] += 1
                return (self.offsets[2] - 1, self.bottom_row)
            case _:
                self.offsets[3] += 1
                return (self.row_length - self.offsets[3], self.bottom_row)
