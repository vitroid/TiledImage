import logging

# external modules
import numpy as np
from tiledimage import Rect, Range


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
        self.region = None
        self.bgcolor = np.array(bgcolor)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # TiledImageは特別なクリーンアップ処理は必要ありません

    def tiles_containing(self, region: Rect, includeempty=False):
        """
        return the tiles containing the given region
        """
        logger = logging.getLogger()
        t = []
        xran = (
            region.x_range.min_val // self.tilesize[0],
            (region.x_range.max_val + self.tilesize[0] - 1) // self.tilesize[0],
        )
        yran = (
            region.y_range.min_val // self.tilesize[1],
            (region.y_range.max_val + self.tilesize[1] - 1) // self.tilesize[1],
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
                    o = tregion & region
                    t.append((tile, o))
        return t

    def get_region(self, region: Rect | None = None):
        logger = logging.getLogger()
        if region is None:
            region = self.region
        image = np.zeros(
            (region.y_range.width, region.x_range.width, 3), dtype=np.uint8
        )
        image[:, :] = self.bgcolor
        for tile, overlap in self.tiles_containing(region):
            if overlap is None:
                continue
            src = self.tiles[tile]
            originx, originy = tile
            image[
                overlap.y_range.min_val
                - region.y_range.min_val : overlap.y_range.max_val
                - region.y_range.min_val,
                overlap.x_range.min_val
                - region.x_range.min_val : overlap.x_range.max_val
                - region.x_range.min_val,
            ] = src[
                overlap.y_range.min_val - originy : overlap.y_range.max_val - originy,
                overlap.x_range.min_val - originx : overlap.x_range.max_val - originx,
            ]
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
                    overlap.y_range.min_val
                    - originy : overlap.y_range.max_val
                    - originy,
                    overlap.x_range.min_val
                    - originx : overlap.x_range.max_val
                    - originx,
                ] = image[
                    overlap.y_range.min_val
                    - region.y_range.min_val : overlap.y_range.max_val
                    - region.y_range.min_val,
                    overlap.x_range.min_val
                    - region.x_range.min_val : overlap.x_range.max_val
                    - region.x_range.min_val,
                ]
            else:
                dy0 = overlap.y_range.min_val - originy
                dy1 = overlap.y_range.max_val - originy
                dx0 = overlap.x_range.min_val - originx
                dx1 = overlap.x_range.max_val - originx
                sx0 = overlap.x_range.min_val - region.x_range.min_val
                sx1 = overlap.x_range.max_val - region.x_range.min_val
                sy0 = overlap.y_range.min_val - region.y_range.min_val
                sy1 = overlap.y_range.max_val - region.y_range.min_val
                src[dy0:dy1, dx0:dx1, :] = (
                    linear_alpha[sx0:sx1, :] * image[sy0:sy1, sx0:sx1, :]
                    + (1 - linear_alpha[sx0:sx1, :]) * src[dy0:dy1, dx0:dx1, :]
                )

            # rewrite the item explicitly (for caching)
            self.tiles[tile] = src
        if self.region is None:
            self.region = region
        else:
            self.region = Rect.from_coords(
                min(self.region.x_range.min_val, region.x_range.min_val),
                max(self.region.x_range.max_val, region.x_range.max_val),
                min(self.region.y_range.min_val, region.y_range.min_val),
                max(self.region.y_range.max_val, region.y_range.max_val),
            )

    def get_image(self):
        return self.get_region(self.region)


def test():
    import sys
    import cv2

    png = sys.argv[1]
    tilesize = int(sys.argv[2])
    with TiledImage(tilesize=tilesize) as cimage:
        cimage.put_image((20, 40), cv2.imread(png))
        cimage.put_image((10, 20), cv2.imread(png))
        image = cimage.get_image()
        cv2.imshow("image", image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    test()
