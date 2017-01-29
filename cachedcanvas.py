import tileimagedb
import hugecanvas
import logging
import cv2
import numpy as np

class CachedCanvas(hugecanvas.HugeCanvas):
    def __init__(self, dir="canvas.pngs", tilesize=128, cachesize=10, clean=True):
        super(CachedCanvas, self).__init__(tilesize)
        self.tiles = tileimagedb.TileImageDB(dir=dir,
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
    
def test():
    debug = True
    if debug:
        logging.basicConfig(level=logging.DEBUG,
                            #filename='log.txt',
                            format="%(asctime)s %(levelname)s %(message)s")
    else:
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
    canvas = CachedCanvas(tilesize=(64,64), cachesize=100)
    img = cv2.imread("sample.png")
    canvas.put_image((-10,-10), img)
    canvas.put_image((100,120), img)
    logger = logging.getLogger()
    logger.debug("start showing.")
    c = canvas.get_image()
    cv2.imshow("canvas",c)
    cv2.waitKey(0)

if __name__ == "__main__":
    test()
