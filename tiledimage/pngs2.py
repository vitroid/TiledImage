#!/usr/bin/env python

from __future__ import print_function

import sys

import cv2

import tiledimage.cachedimage as ci


def main():
    if len(sys.argv) != 3:
        print("Convert an image tile to a single image.\n")
        print("usage: pngs2 from_image.pngs to_image.[jpg|png|...]\n")
        sys.exit(1)
    with ci.CachedImage("inherit", dir=sys.argv[1]) as image:
        image = image.get_image()
        cv2.imwrite(sys.argv[2], image)


if __name__ == "__main__":
    main()
