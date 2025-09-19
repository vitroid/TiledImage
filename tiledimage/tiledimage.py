import logging

# external modules
import numpy as np
from tiledimage import Rect, Range
import cv2


class TiledImage:
    """
    it has no size.
    size is determined by the tiles.
    !!!   it is better to fix the tile size. (128x128, for example)
    """

    def __init__(self, tilesize=128, bgcolor=(100, 100, 100)):
        self.tiles = dict()
        if type(tilesize) is int:
            self.tilesize = (tilesize, tilesize)
        else:
            assert type(tilesize) is tuple
            self.tilesize = tilesize
        self.rect = None
        self.bgcolor = np.array(bgcolor)

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

        return Rect.from_coords(x_start, x_stop, y_start, y_stop)

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

    def tiles_containing(self, rect: Rect, includeempty=False):
        """
        return the tiles containing the given region
        """
        logger = logging.getLogger()
        t = []
        xran = (
            rect.x_range.min_val // self.tilesize[0],
            (rect.x_range.max_val + self.tilesize[0] - 1) // self.tilesize[0],
        )
        yran = (
            rect.y_range.min_val // self.tilesize[1],
            (rect.y_range.max_val + self.tilesize[1] - 1) // self.tilesize[1],
        )
        for ix in range(xran[0], xran[1]):
            for iy in range(yran[0], yran[1]):
                tile = (ix * self.tilesize[0], iy * self.tilesize[1])
                logger.debug("Tile: {0}".format(tile))
                if (tile in self.tiles) or includeempty:
                    tregion = Rect.from_coords(
                        tile[0],
                        tile[0] + self.tilesize[0],
                        tile[1],
                        tile[1] + self.tilesize[1],
                    )
                    o = tregion & rect
                    t.append((tile, o))
        return t

    def get_region(self, rect: Rect | None = None, width: int = 0):
        logger = logging.getLogger()
        if rect is None:
            rect = self.rect
        logger.debug(f"get_region region:{rect}")
        # # region.x_rangeが0:や:infの場合には、それぞれself.regionのx_rangeを使用する
        # if region.x_range.min_val == 0:
        #     region.x_range.min_val = self.region.x_range.min_val
        # if region.x_range.max_val == float("inf"):
        #     region.x_range.max_val = self.region.x_range.max_val
        # if region.y_range.min_val == 0:
        #     region.y_range.min_val = self.region.y_range.min_val
        # if region.y_range.max_val == float("inf"):
        #     region.y_range.max_val = self.region.y_range.max_val

        if width:
            dst_width = width
            dst_height = width * rect.height / rect.width
            scale = width / rect.width
        else:
            dst_width = rect.width
            dst_height = rect.height
            scale = 1.0

        image = np.zeros((dst_height, dst_width, 3), dtype=np.uint8)
        image[:, :] = self.bgcolor
        for tile, overlap in self.tiles_containing(rect):
            if overlap is None:
                continue
            src = self.tiles[tile]
            originx, originy = int(tile[0] * scale), int(tile[1] * scale)
            src_top = overlap.top - originy
            src_bottom = overlap.bottom - originy
            src_left = overlap.left - originx
            src_right = overlap.right - originx
            src_image = src[src_top:src_bottom, src_left:src_right]
            src_image = cv2.resize(src_image, (dst_width, dst_height))

            dst_top = int((overlap.top - rect.top) * scale)
            dst_bottom = int((overlap.bottom - rect.top) * scale)
            dst_left = int((overlap.left - rect.left) * scale)
            dst_right = int((overlap.right - rect.left) * scale)
            image[dst_top:dst_bottom, dst_left:dst_right] = src_image
            # dst_bottom = overlap.bottom-rect.top
            # dst_left = overlap.left-rect.left
            # dst_right = overlap.right-rect.left
            # image[
            #     overlap.y_range.min_val
            #     - rect.y_range.min_val : overlap.y_range.max_val
            #     - rect.y_range.min_val,
            #     overlap.x_range.min_val
            #     - rect.x_range.min_val : overlap.x_range.max_val
            #     - rect.x_range.min_val,
            # ] = src[
            #     overlap.y_range.min_val - originy : overlap.y_range.max_val - originy,
            #     overlap.x_range.min_val - originx : overlap.x_range.max_val - originx,
            # ]
        return image

    def put_image(self, position, image, linear_alpha=None):
        """
        split the existent tiles
        and put a big single tile.
        the image must be larger than a single tile.
        otherwise, a different algorithm is required.
        """
        h, w = image.shape[:2]
        region = Rect.from_coords(
            position[0], position[0] + w, position[1], position[1] + h
        )
        for tile, overlap in self.tiles_containing(region, includeempty=True):
            if overlap is None:
                continue
            if tile not in self.tiles:
                self.tiles[tile] = np.zeros(
                    (self.tilesize[1], self.tilesize[0], 3), dtype=np.uint8
                )
                self.tiles[tile][:, :] = self.bgcolor
            src = self.tiles[tile]
            originx, originy = tile

            if linear_alpha is None:
                src[
                    overlap.top - originy : overlap.bottom - originy,
                    overlap.left - originx : overlap.right - originx,
                ] = image[
                    overlap.top - region.top : overlap.bottom - region.top,
                    overlap.left - region.left : overlap.right - region.left,
                ]
            else:
                dy0 = overlap.top - originy
                dy1 = overlap.bottom - originy
                dx0 = overlap.left - originx
                dx1 = overlap.right - originx
                sx0 = overlap.left - region.left
                sx1 = overlap.right - region.left
                sy0 = overlap.top - region.top
                sy1 = overlap.bottom - region.top
                alpha = linear_alpha[np.newaxis, :, np.newaxis]
                src[dy0:dy1, dx0:dx1, :] = (
                    alpha[:, sx0:sx1, :] * image[sy0:sy1, sx0:sx1, :]
                    + (1 - alpha[:, sx0:sx1, :]) * src[dy0:dy1, dx0:dx1, :]
                )

            # rewrite the item explicitly (for caching)
            self.tiles[tile] = src
        if self.rect is None:
            self.rect = region
        else:
            self.rect = Rect.from_coords(
                min(self.rect.left, region.left),
                max(self.rect.right, region.right),
                min(self.rect.top, region.top),
                max(self.rect.bottom, region.bottom),
            )

    def get_image(self, width: int = 0):
        # widthを指定すると縮小する。
        return self.get_region(self.rect, width)


def test():
    import sys
    import cv2
    import logging

    logging.basicConfig(level=logging.DEBUG)

    png = sys.argv[1]
    tilesize = int(sys.argv[2])
    with TiledImage(tilesize=tilesize) as tiled_image:
        tiled_image[20:, 40:] = cv2.imread(png)
        tiled_image[10:, 20:] = cv2.imread(png)
        image = tiled_image[:, :]
        cv2.imshow("image", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    test()
