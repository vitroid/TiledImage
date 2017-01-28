import cv2

#a range is always spacified with the min and max=min+width
#2d region consists of two ranges.

def overlap(r1, r2):
    """
    True if the give regions (1D) overlap

    there are 6 possible orders
    ( ) [ ] x
    ( [ ) ] o 
    ( [ ] ) o
    [ ( ) ] o
    [ ( ] ) o
    [ ] ( ) x
    ! { ) [ | ] ( }
    ie [ ) && ( ]
    """
    if r1[0] < r2[1] and r2[0] < r1[1]:
        return max(r1[0],r2[0]), min(r1[1], r2[1])
    return None


#It should also return the overlapping region
def overlap2D(r1, r2):
    x = overlap(r1[0], r2[0])
    if x is not None:
        y = overlap(r1[1], r2[1])
        if y is not None:
            return x,y
    return None


class HugeCanvas():
    """
    it has no size.
    size is determined by the tiles.
    !!!   it is better to fix the tile size. (128x128, for example)
    """
    def __init__(self):
        self.tiles = dict()
        self.tilesize = 128
        
    def tiles_containing(self, region):
        """
        return the tiles containing the given region
        """
        t = []
        for tile in self.tiles:
            tregion = ((tile[0], tile[0]+self.tilesize), (tile[1], tile[1]+self.tilesize))
            o = overlap2D(tregion, region):
            t.append((tile, o))
        return t

    def get_region(self, region):
        xrange, yrange = region
        image = np.zeros((yrange[1]-yrange[0], xrange[1] - xrayge[0], 3), dtype=np.uint8)
        for tile, overlap in self.tiles_containing(region):
            originx, originy = tile
            src = tiles[tile]
            h,w = src.shape[:2]
            xr, yr = overlap
            image[yr[0]-yrange[0]:yr[1]-yrange[0], xr[0]-xrange[0]:xr[1]-xrange[0], 3] = src[yr[0]-originy:yr[1]-originy, xr[0]-originx:xr[1]-originx, 3]
        return image

    def put_image(self, position, image):
        """
        split the existent tiles
        and put a big single tile.
        the image must be larger than a single tile.
        otherwise, a different algorithm is required.
        """
        h,w = image.shape[:2]
    
