#!/usr/bin/env python

import sys

import cv2

import tiledimage.cachedimage as ci


def main():
    if len(sys.argv) not in (3, 4):
        print("Convert a image to a tiled image.\n")
        print("usage: pngs2 from_image to_image.pngs [tilesize]\n")
        sys.exit(1)
    tilesize = 64
    if len(sys.argv) == 4:
        tilesize = int(sys.argv[3])
    image = cv2.imread(sys.argv[1])
    cimage = ci.CachedImage("new", dir=sys.argv[2], tilesize=(tilesize, tilesize))
    cimage.put_image((0, 0), image)
    # cimage.done()


if __name__ == "__main__":
    main()
