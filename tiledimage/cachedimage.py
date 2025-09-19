from logging import getLogger, basicConfig, DEBUG, INFO

import json
import numpy as np

from tiledimage.tiledimage import TiledImage
import tiledimage.tilecache as tilecache
from tiledimage import Rect, Range


class CachedImage(TiledImage):
    def __init__(
        self,
        mode,
        dir="image.pngs",
        tilesize=128,
        cachesize=10,
        fileext="png",
        bgcolor=(0, 0, 0),
        hook=None,
        disposal=False,
    ):
        """
        if mode == "new", flush the dir.
        hook is a function like put_image, that is called then a tile is rewritten.
        dir will be removed when disposal is True.
        """
        # logger = getLogger()
        super(CachedImage, self).__init__(tilesize)
        self.fileext = fileext
        self.bgcolor = bgcolor
        self.disposal = disposal
        self.dir = dir
        self.modified = False
        if mode == "inherit":
            # read the info.txt in the dir.
            self.region = [None, None]
            try:
                with open(f"{dir}/info.json", "r") as file:
                    info = json.load(file)
                    self.region = Rect(
                        x_range=Range(
                            min_val=info["xrange"][0], max_val=info["xrange"][1]
                        ),
                        y_range=Range(
                            min_val=info["yrange"][0], max_val=info["yrange"][1]
                        ),
                    )
                    self.tilesize = info["tilesize"]
                    self.bgcolor = info["bgcolor"]
                    self.fileext = info["filetype"]
            except FileNotFoundError:
                # backward compatibility
                xrange = None
                yrange = None
                with open(f"{dir}/info.txt", "r") as file:
                    while True:
                        line = file.readline().strip()
                        if len(line) == 0:
                            break
                        cols = line.split(" ")
                        if cols[-1] == "xrange":
                            xrange = Range(min_val=int(cols[0]), max_val=int(cols[1]))
                        if cols[-1] == "yrange":
                            yrange = Range(min_val=int(cols[0]), max_val=int(cols[1]))
                        if cols[-1] == "tilesize":
                            self.tilesize = [int(cols[0]), int(cols[1])]
                        if cols[-1] == "bgcolor":
                            self.bgcolor = [int(cols[0]), int(cols[1]), int(cols[2])]
                        if cols[-1] == "filetype":
                            self.fileext = cols[-1]
                self.region = Rect(x_range=xrange, y_range=yrange)
        defaulttile = np.zeros((self.tilesize[1], self.tilesize[0], 3), dtype=np.uint8)
        self.bgcolor = np.array(self.bgcolor)
        # logger.info("Color: {0}".format(self.bgcolor))
        defaulttile[:, :, :] = self.bgcolor[:3]
        # logger.info("Tile: {0}".format(defaulttile))
        self.tiles = tilecache.TileCache(
            mode,
            dir=dir,
            cachesize=cachesize,
            fileext=self.fileext,
            default=defaulttile,
            hook=hook,
        )
        # just for done()
        self.dir = dir

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.modified:
            self._write_info()
        if self.disposal:
            rmdir(self.dir)

    def _write_info(self):
        """
        内部実装用：情報をJSONファイルに書き出す
        """
        bgcolor = self.bgcolor
        if isinstance(bgcolor, np.ndarray):
            bgcolor = bgcolor.tolist()
        info = dict(
            xrange=self.region.x_range.as_list(),
            yrange=self.region.y_range.as_list(),
            tilesize=self.tilesize,
            bgcolor=bgcolor,
            filetype=self.fileext,
        )
        with open(f"{self.dir}/info.json", "w") as file:
            json.dump(info, file)
        self.tiles.done()  # タイルキャッシュの終了処理を呼び出す

    def put_image(self, pos, img, linear_alpha=None):
        super(CachedImage, self).put_image(pos, img, linear_alpha)
        self.modified = True
        logger = getLogger()
        nmiss, naccess, cachesize = self.tiles.cachemiss()
        logger.info(
            "Cache miss {0}% @ {1} tiles".format(nmiss * 100 // naccess, cachesize)
        )
        self.tiles.adjust_cache_size()

    def set_hook(self, hook):
        self.tiles.set_hook(hook)


def test():
    import sys
    import cv2

    png = sys.argv[1]
    tilesize = int(sys.argv[2])
    with CachedImage("new", tilesize=tilesize) as tiled_image:
        tiled_image[10:, 20:] = cv2.imread(png)
        tiled_image[-10:, -20:] = cv2.imread(png)
        image = tiled_image[:, :]

    with CachedImage("inherit", dir="image.pngs") as tiled_image:
        cv2.imshow("image", tiled_image[:, :])
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    test()
