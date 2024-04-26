#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.webscraper import MapyCZServer

if __name__ == '__main__':
    # port a host nastavi kde je spusten serverovy soket
    # scrapeAroundAutomatically - automaticky ukladat do cache okolni tily
    # scrapeAroundWorkerCount - pocet workeru okoniho scrapovani ^
    # maxConnections je jen orientacni hodnota
    # sessionCount je pocet soucasnych pripojeni k mapy.cz serveru
    server: MapyCZServer = MapyCZServer(port=999, host="192.168.1.66",
                                        scrapeAroundAutomatically=False,
                                        scrapeAroundWorkerCount=1,
                                        maxConnections=10,
                                        sessionCount=5)
    # Ukladani tilu do cache (cesta a maximalni velikost v poctu tilu)
    # maximalni velikost je orientacni, worker maze prebytecne soubory (__cleanExcessCacheItems)
    server.cache(r"C:\Temp\mapyCZCache", 1000)
    print(f"Server listening on http://{server.host}:{server.port}")
    server.listen()
