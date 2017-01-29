#!/usr/bin/env python3

import cachedimage as ci
import sys
import cv2

image = ci.CachedImage("inherit", dir=sys.argv[1]).get_image()
cv2.imwrite(sys.argv[2], image)
