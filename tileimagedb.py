import cv2
import pylru #"Least Recent Used" type cache
import os
import logging
import shutil

def remove_folder(path):
    # check if folder exists
    if os.path.exists(path):
        # remove if exists
        shutil.rmtree(path)
    
class TileImageDB():
    """
    A tile of images that are mostly stored in files
    """
    def __init__(self, dir="tileimage", cachesize=10, default=None):
        remove_folder(dir)
        os.mkdir(dir)
        self.dir = dir
        self.cache = pylru.lrucache(cachesize, callback=self.writeback)
        
    def key_to_filename(self, key):
        return "{0}/{1},{2}.png".format(self.dir, *key)
    
    def __getitem__(self, key):
        logger = logging.getLogger()
        logger.debug("getitem key:{0}".format(key))
        try:
            value = self.cache[key]
        except KeyError:
            logger.debug("cache miss key:{0}".format(key))
            filename = self.key_to_filename(key)
            if os.path.exists(filename):
                value = cv2.imread(filename)
            else:
                value = default
            self.cache[key] = value
        return value

    def __setitem__(self, key, value):
        self.cache[key] = value
            

    def writeback(self, key, value):
        """
        write back when it is purged from cache
        """
        logger = logging.getLogger()
        logger.info("purge key:{0}".format(key))
        filename = self.key_to_filename(key)
        cv2.imwrite(filename, value)
        
    def __contains__(self, key):
        filename = self.key_to_filename(key)
        return os.path.exists(filename)
        
    def done(self):
        remove_folder(self.dir)
        

