import logging

# external modules
import numpy as np
from pyperbox import Rect


class SimpleImage:

    def __init__(self, bgcolor=(100, 100, 100)):
        self.rect = None
        self.bgcolor = np.array(bgcolor, dtype=np.uint8)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # TiledImageは特別なクリーンアップ処理は必要ありません

    def _parse_slice(self, key):
        """スライスを解析してRectに変換する

        Args:
            key: スライスまたはタプル。例: (slice(0, 10), slice(0, 20))

        Returns:
            Rect: スライスに対応する領域
        """
        if not isinstance(key, tuple) or len(key) != 2:
            raise IndexError("2次元のスライスを指定してください")

        y_slice, x_slice = key
        if not (isinstance(y_slice, slice) and isinstance(x_slice, slice)):
            raise IndexError("スライスを指定してください")

        # スライスの開始と終了を取得
        y_start = y_slice.start if y_slice.start is not None else 0
        y_stop = y_slice.stop if y_slice.stop is not None else float("inf")
        x_start = x_slice.start if x_slice.start is not None else 0
        x_stop = x_slice.stop if x_slice.stop is not None else float("inf")

        # ステップは未対応
        if y_slice.step is not None or x_slice.step is not None:
            raise NotImplementedError("ステップ付きスライスには未対応です")

        return Rect.from_bounds(x_start, x_stop, y_start, y_stop)

    def __getitem__(self, key):
        """スライスで領域を取得する

        Example:
            image = tiled_image[10:20, 30:40]  # 10:20行、30:40列の領域を取得
        """
        region = self._parse_slice(key)
        return self.get_region(region)

    def __setitem__(self, key, value):
        """スライスで領域を設定する

        Example:
            tiled_image[10:20, 30:40] = image  # 10:20行、30:40列の領域に画像を設定
        """
        if not isinstance(value, np.ndarray):
            raise TypeError("NumPy配列を指定してください")

        region = self._parse_slice(key)
        self.put_image((region.x_range.min_val, region.y_range.min_val), value)

    def get_region(self, rect: Rect | None = None):
        logger = logging.getLogger()
        if rect is None:
            rect = self.rect
        if rect is None:
            return
        logger.debug(f"get_region region:{rect}")
        # # region.x_rangeが0:や:infの場合には、それぞれself.regionのx_rangeを使用する
        if rect.left == 0:
            rect.x_range.min_val = self.rect.left
        if rect.right == float("inf"):
            rect.x_range.max_val = self.rect.right
        if rect.top == 0:
            rect.y_range.min_val = self.rect.top
        if rect.bottom == float("inf"):
            rect.y_range.max_val = self.rect.bottom

        dst_width = rect.width
        dst_height = rect.height

        image = np.zeros((dst_height, dst_width, 3), dtype=np.uint8) + self.bgcolor
        crop = self.rect & rect
        image[
            crop.top - rect.top : crop.bottom - rect.top,
            crop.left - rect.left : crop.right - rect.left,
        ] = self.image[
            crop.top - self.rect.top : crop.bottom - self.rect.top,
            crop.left - self.rect.left : crop.right - self.rect.left,
        ]
        return image

    def put_image(self, position, image, linear_alpha=None, full_alpha=None):
        """
        split the existent tiles
        and put a big single tile.
        the image must be larger than a single tile.
        otherwise, a different algorithm is required.
        """
        h, w = image.shape[:2]
        rect = Rect.from_bounds(
            position[0], position[0] + w, position[1], position[1] + h
        )
        # expand the canvas
        if self.rect is None:
            self.rect = rect
            self.image = image.copy()
        else:
            newrect = self.rect | rect
            new_image = (
                np.zeros([newrect.height, newrect.width, 3], dtype=np.uint8)
                + self.bgcolor
            )
            new_image[
                self.rect.top - newrect.top : self.rect.bottom - newrect.top,
                self.rect.left - newrect.left : self.rect.right - newrect.left,
            ] = self.image
            self.image = new_image
            self.rect = newrect

            if linear_alpha is None and full_alpha is None:
                self.image[
                    rect.top - self.rect.top : rect.bottom - self.rect.top,
                    rect.left - self.rect.left : rect.right - self.rect.left,
                ] = image
            else:
                if full_alpha is not None:
                    alpha = full_alpha[:, :, np.newaxis]
                else:
                    alpha = linear_alpha[np.newaxis, :, np.newaxis]
                self.image[
                    rect.top - self.rect.top : rect.bottom - self.rect.top,
                    rect.left - self.rect.left : rect.right - self.rect.left,
                    :,
                ] = (
                    alpha * image
                    + (1 - alpha)
                    * self.image[
                        rect.top - self.rect.top : rect.bottom - self.rect.top,
                        rect.left - self.rect.left : rect.right - self.rect.left,
                        :,
                    ]
                )

    def get_image(self):
        # widthを指定すると縮小する。
        return self.get_region(self.rect)


def test():
    import sys
    import cv2
    import logging

    logging.basicConfig(level=logging.DEBUG)

    png = sys.argv[1]
    with SimpleImage() as canvas:
        canvas[20:, 40:] = cv2.imread(png)
        canvas[10:, 20:] = cv2.imread(png)
        image = canvas[:, :]
        cv2.imshow("image", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    test()
