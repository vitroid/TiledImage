__version__ = "1.0.0"

from dataclasses import dataclass


@dataclass
class Range:
    """数値の範囲を表現するクラス

    Attributes:
        min_val (int): 範囲の最小値
        max_val (int): 範囲の最大値（min_val + width）
    """

    min_val: int
    max_val: int

    @property
    def width(self) -> int:
        """範囲の幅を返す"""
        return self.max_val - self.min_val

    def overlaps(self, other: "Range") -> bool:
        """他の範囲と重複があるかどうかを判定する"""
        return self.min_val < other.max_val and other.min_val < self.max_val

    def get_overlap(self, other: "Range") -> "Range | None":
        """他の範囲との重複部分を返す。重複がない場合はNoneを返す"""
        if self.overlaps(other):
            return Range(
                max(self.min_val, other.min_val), min(self.max_val, other.max_val)
            )
        return None

    def __and__(self, other: "Range") -> "Range | None":
        """&演算子で範囲の重複を取得する

        Example:
            r1 = Range(0, 10)
            r2 = Range(5, 15)
            overlap = r1 & r2  # Range(5, 10)
        """
        return self.get_overlap(other)

    def as_list(self) -> list[int]:
        """範囲をリストに変換する"""
        return [self.min_val, self.max_val]

    def validate(self, min_size: int = 0):
        if self.min_val >= self.max_val:
            raise ValueError("Invalid region")
        if self.max_val - self.min_val < min_size:
            raise ValueError("Region is too small")


@dataclass
class Rect:
    """2次元の領域を表現するクラス

    Attributes:
        x_range (Range): X方向の範囲
        y_range (Range): Y方向の範囲
    """

    x_range: Range
    y_range: Range

    @classmethod
    def from_coords(cls, x_min: int, x_max: int, y_min: int, y_max: int) -> "Rect":
        """座標からAreaを作成する

        Args:
            x_min: X方向の最小値
            x_max: X方向の最大値
            y_min: Y方向の最小値
            y_max: Y方向の最大値
        """
        return cls(Range(x_min, x_max), Range(y_min, y_max))

    @property
    def width(self) -> int:
        """領域の幅を返す"""
        return self.x_range.width

    @property
    def height(self) -> int:
        """領域の高さを返す"""
        return self.y_range.width

    def overlaps(self, other: "Rect") -> bool:
        """他の領域と重複があるかどうかを判定する"""
        return self.x_range.overlaps(other.x_range) and self.y_range.overlaps(
            other.y_range
        )

    def get_overlap(self, other: "Rect") -> "Rect | None":
        """他の領域との重複部分を返す。重複がない場合はNoneを返す"""
        x_overlap = self.x_range & other.x_range
        y_overlap = self.y_range & other.y_range
        if x_overlap is not None and y_overlap is not None:
            return Rect(x_overlap, y_overlap)
        return None

    def __and__(self, other: "Rect") -> "Rect | None":
        """&演算子で領域の重複を取得する

        Example:
            a1 = Area.from_coords(0, 10, 0, 10)
            a2 = Area.from_coords(5, 15, 5, 15)
            overlap = a1 & a2  # Area(Range(5, 10), Range(5, 10))
        """
        return self.get_overlap(other)

    def trim(self, image_shape: tuple[int, int]) -> Rect:
        """
        画像の範囲を超える領域をtrimする。
        """
        top = max(0, self.y_range.min_val)
        bottom = min(image_shape[0], self.y_range.max_val)
        left = max(0, self.x_range.min_val)
        right = min(image_shape[1], self.x_range.max_val)
        return Rect(
            x_range=Range(min_val=left, max_val=right),
            y_range=Range(min_val=top, max_val=bottom),
        )

    def to_cvrect(self) -> tuple[int, int, int, int]:
        return (
            self.x_range.min_val,
            self.y_range.min_val,
            self.width,
            self.height,
        )
