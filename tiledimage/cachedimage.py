from logging import getLogger, basicConfig, DEBUG, INFO

import json
import numpy as np

from tiledimage.tiledimage import TiledImage
import tiledimage.tilecache as tilecache


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
            with open(f"{dir}/info.json", "r") as file:
                info = json.load(file)
                self.region[0] = info["xrange"]
                self.region[1] = info["yrange"]
                self.tilesize = info["tilesize"]
                self.bgcolor = info["bgcolor"]
                self.fileext = info["filetype"]
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
            xrange=self.region[0],
            yrange=self.region[1],
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
