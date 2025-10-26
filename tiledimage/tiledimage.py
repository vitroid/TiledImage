import logging

# external modules
import numpy as np
from pyperbox import Rect, Range
import cv2

from tiledimage.simpleimage import SimpleImage


class TiledImage(SimpleImage):
    """
    it has no size.
    size is determined by the tiles.
    !!!   it is better to fix the tile size. (128x128, for example)
    """

    def __init__(self, tilesize=128, bgcolor=(100, 100, 100)):
        super(TiledImage, self).__init__(bgcolor)
        self.tiles = dict()
        if type(tilesize) is int:
            self.tilesize = (tilesize, tilesize)
        else:
            assert type(tilesize) is tuple
            self.tilesize = tilesize

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
                    tregion = Rect.from_bounds(
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

        if width:
            dst_width = int(width)
            dst_height = int(width * rect.height) // rect.width
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
            if src is None:
                continue
            originx, originy = tile
            src_top = overlap.top - originy
            src_bottom = overlap.bottom - originy
            src_left = overlap.left - originx
            src_right = overlap.right - originx
            src_image = src[src_top:src_bottom, src_left:src_right]

            dst_top = int((overlap.top - rect.top) * scale)
            dst_bottom = int((overlap.bottom - rect.top) * scale)
            dst_left = int((overlap.left - rect.left) * scale)
            dst_right = int((overlap.right - rect.left) * scale)

            src_image = cv2.resize(
                src_image, (dst_right - dst_left, dst_bottom - dst_top)
            )
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
        else:
            self.rect |= rect
        for tile, overlap in self.tiles_containing(rect, includeempty=True):
            if overlap is None:
                continue
            if tile not in self.tiles:
                self.tiles[tile] = np.zeros(
                    (self.tilesize[1], self.tilesize[0], 3), dtype=np.uint8
                )
                self.tiles[tile][:, :] = self.bgcolor
            src = self.tiles[tile]
            originx, originy = tile

            dy0 = overlap.top - originy
            dy1 = overlap.bottom - originy
            dx0 = overlap.left - originx
            dx1 = overlap.right - originx
            sx0 = overlap.left - rect.left
            sx1 = overlap.right - rect.left
            sy0 = overlap.top - rect.top
            sy1 = overlap.bottom - rect.top
            if linear_alpha is None and full_alpha is None:
                src[
                    dy0:dy1,
                    dx0:dx1,
                ] = image[
                    sy0:sy1,
                    sx0:sx1,
                ]
            else:
                if full_alpha is not None:
                    alpha = full_alpha[:, :, np.newaxis]
                    src[dy0:dy1, dx0:dx1, :] = (
                        alpha[sy0:sy1, sx0:sx1, :] * image[sy0:sy1, sx0:sx1, :]
                        + (1 - alpha[sy0:sy1, sx0:sx1, :]) * src[dy0:dy1, dx0:dx1, :]
                    )
                else:
                    alpha = linear_alpha[np.newaxis, :, np.newaxis]
                    src[dy0:dy1, dx0:dx1, :] = (
                        alpha[:, sx0:sx1, :] * image[sy0:sy1, sx0:sx1, :]
                        + (1 - alpha[:, sx0:sx1, :]) * src[dy0:dy1, dx0:dx1, :]
                    )

            # rewrite the item explicitly (for caching)
            self.tiles[tile] = src

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
        image = tiled_image.get_image(width=100)
        cv2.imshow("image", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    test()
