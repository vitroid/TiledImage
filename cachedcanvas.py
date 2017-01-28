import tileimagedb
import hugecanvas
import logging
import cv2
import numpy as np

class CachedCanvas(hugecanvas.HugeCanvas):
    def __init__(self, tilesize=128, cachesize=10):
        super(CachedCanvas, self).__init__(tilesize)
        self.tiles = tileimagedb.TileImageDB(dir="testdir",cachesize=cachesize,default=np.zeros((tilesize,tilesize,3), dtype=np.uint8))

    def done(self):
        self.tiles.done()
    
def test():
    debug = True
    if debug:
        logging.basicConfig(level=logging.DEBUG,
                            #filename='log.txt',
                            format="%(asctime)s %(levelname)s %(message)s")
    else:
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
    canvas = CachedCanvas(64)
    img = cv2.imread("sample.png")
    canvas.put_image((-10,-10), img)
    canvas.put_image((100,120), img)
    c = canvas.get_full()
    cv2.imshow("canvas",c)
    cv2.waitKey(0)

if __name__ == "__main__":
    test()
