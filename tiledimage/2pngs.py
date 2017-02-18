#!/usr/bin/env python

from __future__ import print_function
from tiledimage import cachedimage as ci
import sys
import cv2


def main():
    if len(sys.argv) not in (3,4):
        print("Convert a image to a tiled image.\n")
        print("usage: pngs2 from_image to_image.pngs [tilesize]\n")
        sys.exit(1)
    tilesize=64
    if len(sys.argv)==4:
        tilesize=int(sys.argv[3])
    image = cv2.imread(sys.argv[1])
    cimage = ci.CachedImage("new", dir=sys.argv[2])
    cimage.put_image((0,0), image)
    cimage.done()

if __name__ == "__main__":
    main()
