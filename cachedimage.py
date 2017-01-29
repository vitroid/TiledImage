import tilecache
import tiledimage
import logging
import cv2
import numpy as np

class CachedImage(tiledimage.TiledImage):
    def __init__(self, dir="image.pngs", tilesize=128, cachesize=10, clean=True):
        super(CachedImage, self).__init__(tilesize)
        self.tiles = tilecache.TileCache(dir=dir,
                                             cachesize=cachesize,
                                             default=np.zeros((self.tilesize[1],self.tilesize[0],3), dtype=np.uint8))
        #just for done()
        self.clean = clean
        self.dir   = dir   
        
    def done(self):
        with open(self.dir + "/info.txt", "w") as file:
            file.write("{0} {1} xrange\n".format(*self.region[0]))
            file.write("{0} {1} yrange\n".format(*self.region[1]))
            file.write("{0} {1} tilesize\n".format(*self.tilesize))
            file.write("0 0 0 background\n")   #0..255, black
        self.tiles.done(self.clean)

    def put_image(self, pos, img, linear_alpha=None):
        super(CachedImage, self).put_image(pos, img, linear_alpha)
        logger = logging.getLogger()
        nmiss, naccess, cachesize = self.tiles.cachemiss()
        logger.info("Cache miss {0}% @ {1}".format(nmiss*100//naccess, cachesize))
        self.tiles.adjust_cache_size()
        
        
def test():
    debug = True
    if debug:
        logging.basicConfig(level=logging.DEBUG,
                            #filename='log.txt',
                            format="%(asctime)s %(levelname)s %(message)s")
    else:
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
    image = CachedImage(tilesize=(64,64), cachesize=100)
    img = cv2.imread("sample.png")
    image.put_image((-10,-10), img)
    image.put_image((100,120), img)
    logger = logging.getLogger()
    logger.debug("start showing.")
    c = image.get_image()
    cv2.imshow("image",c)
    cv2.waitKey(0)

if __name__ == "__main__":
    test()
