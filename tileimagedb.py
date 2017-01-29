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
        self.nget = 0
        self.nmiss = 0
        
    def key_to_filename(self, key):
        return "{0}/{1},{2}.png".format(self.dir, *key)
    
    def __getitem__(self, key):
        logger = logging.getLogger()
        logger.debug("getitem key:{0}".format(key))
        self.nget += 1
        try:
            modified, value = self.cache[key]
        except KeyError:
            self.nmiss += 1
            logger.debug("cache miss key:{0}".format(key))
            filename = self.key_to_filename(key)
            if os.path.exists(filename):
                value = cv2.imread(filename)
            else:
                value = default
            self.cache[key] = [False, value]
        #Automatically optimize the cache size
        if self.nmiss*100//self.nget > 20:
            self.cache.addTailNode(1)
            logger.info("Cache miss: {0}% @ {1}".format(self.nmiss*100//self.nget, self.cache.size()))
        return value

    def __setitem__(self, key, value):
        logger = logging.getLogger()
        logger.debug("update key:{0}".format(key))
        self.cache[key] = [True, value]
            
    def writeback(self, key, value):
        """
        write back when it is purged from cache
        """
        logger = logging.getLogger()
        if value[0]:
            #logger.info("purge key:{0}".format(key))
            filename = self.key_to_filename(key)
            cv2.imwrite(filename, value[1])
        
    def __contains__(self, key):
        if key in self.cache:
            return True
        filename = self.key_to_filename(key)
        return os.path.exists(filename)
        
    def done(self, clean):
        if clean:
            remove_folder(self.dir)
        else:
            #purge the cached images to disk
            for k in self.cache:
                self.writeback(k, self.cache.peek(k))  #peek do not affect the order
        logger = logging.getLogger()
        logger.info("Cache miss: {0}%".format(self.nmiss*100//self.nget))
