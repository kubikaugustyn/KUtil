#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.webscraper import MapyCZServer

if __name__ == '__main__':
    server: MapyCZServer = MapyCZServer(port=999, scrapeAroundAutomatically=True, scrapeAroundWorkerCount=1)
    server.cache(r"C:\Temp\mapyCZCache")
    server.maxCacheSize = 10_000
    server.listen()
