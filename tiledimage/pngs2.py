#!/usr/bin/env python

from __future__ import print_function
from tiledimage import cachedimage as ci
import sys
import cv2


def main():
    if len(sys.argv) != 3:
        print("Convert an image tile to a single image.\n")
        print("usage: pngs2 from_image.pngs to_image.[jpg|png|...]\n")
        sys.exit(1)
    image = ci.CachedImage("inherit", dir=sys.argv[1]).get_image()
    cv2.imwrite(sys.argv[2], image)

if __name__ == "__main__":
    main()
