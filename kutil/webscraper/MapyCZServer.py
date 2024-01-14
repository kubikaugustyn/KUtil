#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import json
import re
import time
from typing import Optional
import requests  # Sadly, Mapy.cz only supports HTTPS, which KUtil doesn't
from requests.cookies import RequestsCookieJar
import os
from enum import Enum, unique
from threading import Thread, enumerate as enum_threads

from kutil.threads.ThreadWaiter import ThreadWaiter
from kutil.protocol.HTTP.HTTPHeaders import HTTPHeaders
from kutil.protocol.HTTP.HTTPResponse import HTTPResponse
from kutil.protocol.HTTP.HTTPRequest import HTTPRequest
from kutil.protocol.HTTPServer import HTTPServerConnection
from kutil.protocol.URLSearchParams import URLSearchParams

from kutil.webscraper.WebScraperServer import WebScraperServer


@unique
class MapSet(Enum):
    ZAKLADNI = "basic"
    TURISTICKA = "outdoor"
    LETECKA = "aerial"
    POPISKY_A_HRANICE = "names-overlay"
    ZIMNI = "winter"


class MapyCZServer(WebScraperServer):
    usageHTMLTemplate: Optional[bytes] = None

    __scrapeAroundArgs: list[tuple]
    __cachedAPIKey: Optional[str]
    # Path to a cache directory, should be shared between users and not contain any sensitive data
    __cachePath: Optional[str]
    # Maximum size in images count stored
    maxCacheSize: Optional[int]
    # Whether you want to start a new thread that will scrape tiles around your requested tile,
    # since you will probably want to move around
    __scrapeAroundAutomatically: bool
    __scrapeAroundWorkerWaiter: ThreadWaiter
    __cacheSizeLimiterWaiter: ThreadWaiter

    def __init__(self, port: int = 666, host: str = "localhost",
                 scrapeAroundAutomatically: bool = False,
                 scrapeAroundWorkerCount: int = 1):
        super().__init__(port, host)
        self.__scrapeAroundArgs = []
        self.__cachedAPIKey = None
        self.__cachePath = None
        self.maxCacheSize = None
        self.__scrapeAroundAutomatically = scrapeAroundAutomatically
        self.__scrapeAroundWorkerWaiter = ThreadWaiter()
        self.__cacheSizeLimiterWaiter = ThreadWaiter()
        if scrapeAroundAutomatically:
            for i in range(scrapeAroundWorkerCount):
                t = Thread(target=self.__scrapeAroundWorker)
                t.name = f"Scrape around worker #{i}"
                t.start()
        t = Thread(target=self.__cleanExcessCacheItems)
        t.name = f"Cache size limiter worker"
        t.start()

    def cache(self, cachePath: str):
        if cachePath is None:
            self.__cachePath = None
            return
        assert os.path.exists(cachePath) and os.path.isdir(cachePath), "Invalid cache directory"
        self.__cachePath = cachePath

    def onDataInner(self, conn: HTTPServerConnection, req: HTTPRequest) -> HTTPResponse:
        query = req.requestURI[req.requestURI.index("?"):] if "?" in req.requestURI else ""
        params: URLSearchParams = URLSearchParams(query)
        uriWithoutQuery = req.requestURI.split("?", maxsplit=1)[0]
        if req.requestURI.startswith("/tile/"):
            mapSetStr = uriWithoutQuery[6:]
            try:
                mapSet = MapSet(mapSetStr)
            except (KeyError, TypeError, ValueError):
                resp = WebScraperServer.badRequest()
                resp.body = HTTPResponse.enc(
                    f'<h1>Bad request - unknown layer kind: {mapSetStr}</h1>'
                    f'<a href="https://developer.mapy.cz/rest-api/funkce/mapove-dlazdice/">'
                    f'Visit this page for more info</a><br>'
                    f'Possible kinds:<br>{"<br>".join(map(lambda item: f"{item.name}: <b>{item.value}</b>", MapSet))}')
                return resp
            try:
                x = int(params["x"])
                y = int(params["y"])
                zoom = int(params["z"])
                tileSize = params.get("tileSize", "256")
                lang = params.get("lang", "cs")
                # https://api.mapy.cz/v1/docs/maptiles/#/tiles/get_v1_maptiles__mapset___tileSize___z___x___y_
                assert tileSize in ("256", "256@2x"), "Invalid tile size"
                if tileSize == "256@2x":
                    assert mapSet in (MapSet.ZAKLADNI, MapSet.TURISTICKA, MapSet.ZIMNI), \
                        "Invalid tile size - used 256@2x in other mapSet than ZAKLADNI, TURISTICKA, ZIMNI"
                assert lang in ("cs", "de", "el", "en", "es", "fr", "it", "nl", "pl", "pt",
                                "ru", "sk", "tr", "uk"), "Invalid language"
            except (ValueError, KeyError, AssertionError) as e:
                resp = WebScraperServer.badRequest()
                resp.body = (b'<h1>Bad request - bad params</h1>'
                             b'Required params: x, y, z (zoom), tileSize ("256" or "256@2x", by default "256"), lang '
                             b'(language - one of: cs - default, de, el, en, es, fr, it, nl, pl, pt, ru, sk, tr, uk)' +
                             HTTPResponse.enc("<br>Caused by error: " + str(e)))
                return resp
            # Scrape for the image
            image: bytes = self.__scrape(x, y, zoom, tileSize, mapSet, lang)
            # Form a response
            headers: HTTPHeaders = HTTPHeaders()
            headers["Content-Type"] = "image/png"
            resp: HTTPResponse = HTTPResponse(200, "OK", headers, image)
            return resp
        elif req.requestURI == "/api_key.txt":
            headers: HTTPHeaders = HTTPHeaders()
            headers["Content-Type"] = "text/plain"
            resp: HTTPResponse = HTTPResponse(200, "OK", headers,
                                              HTTPResponse.enc(self.__obtainAPIKey()))
            return resp
        elif req.requestURI == "/api_key.json":
            headers: HTTPHeaders = HTTPHeaders()
            headers["Content-Type"] = "application/json"
            try:
                body = {"key": self.__obtainAPIKey(), "error": False}
            except Exception as e:
                body = {"key": None, "error": True, "error_str": str(e)}
            resp: HTTPResponse = HTTPResponse(200, "OK", headers,
                                              HTTPResponse.enc(json.dumps(body)))
            return resp
        elif uriWithoutQuery == "/routing/route":
            # https://api.mapy.cz/v1/docs/routing/
            assert len(params.params) > 0, "Query params are required"
            uri = f"https://api.mapy.cz/v1/routing/route?{params}&apikey=API"
        elif req.requestURI.startswith("/geocoding/"):
            # https://api.mapy.cz/v1/docs/geocode/
            assert len(params.params) > 0, "Query params are required"
            kind = uriWithoutQuery[11:]
            assert kind in ("rgeocode", "geocode", "suggest"), "Invalid kind"
            uri = f"https://api.mapy.cz/v1/{kind}?{params}&apikey=API"
        else:
            # If a bad endpoint is requested, show the usage page
            return self.__getUsage()
        return self.__performRequest(uri)

    def __getUsage(self) -> HTTPResponse:
        html: bytes = MapyCZServer.__getUsageHTMLTemplate()
        html = html.replace(b'${HOST}', HTTPResponse.enc(self.host))
        html = html.replace(b'${PORT}', HTTPResponse.enc(str(self.port)))
        headers: HTTPHeaders = HTTPHeaders()
        headers["Content-Type"] = "text/html"
        resp: HTTPResponse = HTTPResponse(200, "OK", headers, html)
        return resp

    def __performRequest(self, uri: str) -> HTTPResponse:
        r = self.__authorizedGetRequest(uri, force200=False)
        headers = HTTPHeaders()
        for name, value in r.headers.lower_items():
            if name not in ("content-type", "content-encoding"):
                continue
            headers[name] = value
        resp = HTTPResponse(r.status_code, r.reason, headers, r.content)
        return resp

    def __obtainAPIKey(self, forceReObtain: bool = False) -> str:
        if self.__cachedAPIKey is not None and not forceReObtain:
            return self.__cachedAPIKey
        r = requests.get("https://api.mapy.cz/virtual-key.js")
        assert r.status_code == 200, f"Bad status code ({r.status_code}) - __scrape failed - API key obtaining"
        self.__cachedAPIKey = re.match('Loader\\.apiKey = "(\\S+)"', r.text).group(1)
        return self.__cachedAPIKey

    def __authorizedGetRequest(self, uri: str, force200: bool = True) -> requests.Response:
        r = requests.get(uri.replace("API", self.__obtainAPIKey()))
        # print(r.url)
        if r.status_code != 200:
            r = requests.get(uri.replace("API", self.__obtainAPIKey(True)))
        if force200:
            assert r.status_code == 200, f"Bad status code ({r.status_code}) - scrape failed - response obtaining"
        return r

    def __scrape(self, x: int, y: int, zoom: int, tileSize: str, mapSet: MapSet, lang: str,
                 canScrapeAround: bool = True) -> bytes:
        # print(f'X: {x}, Y: {y}, Zoom: {zoom}, tile size: {tileSize}, kind: {mapSet.name}, language: {lang}')
        cachedValue: bytes | None = self.__obtainFromCache(x, y, zoom, tileSize, mapSet, lang)
        if cachedValue is not None:
            return cachedValue
        # https://api.mapy.cz/v1/maptiles/outdoor/tiles.json?apikey=virtual-
        # https://api.mapy.cz/v1/docs/maptiles/#/
        # uri: str = f"https://api.mapy.cz/v1/maptiles/outdoor/256@2x/{zoom}/{x}/{y}?apikey=API"
        uri: str = f"https://api.mapy.cz/v1/maptiles/{mapSet.value}/{tileSize}/{zoom}/{x}/{y}?apikey=API&lang={lang}"
        r = self.__authorizedGetRequest(uri)
        self.__storeToCache(x, y, zoom, tileSize, mapSet, lang, r.content)
        if self.__scrapeAroundAutomatically and canScrapeAround:
            self.__scrapeAroundArgs.append((x, y, zoom, tileSize, mapSet, lang))
            self.__scrapeAroundWorkerWaiter.reset()  # Reset + release
        # print(f"Currently running threads: {len(enum_threads())}, "
        #       f"scrape around waiting count: {self.__scrapeAroundWorkerWaiter.waitingThreadCount}")
        return r.content
        """assert kind == LayerKind.BASIC
        # https://api.mapy.cz/v5/config.js?key=&v=5.5.8
        targetUri = f"https://mapserver.mapy.cz/base-m/retina/{zoom}-{x}-{y}"
        cookies: RequestsCookieJar = RequestsCookieJar()
        # Set the cookies to make it work
        cookies["szncsr"] = str(int(time.time()))
        cookies["last-redirect"] = "1"
        MapyCZServer.__setCookies(cookies,
                                requests.get(f"https://mapy.cz/zakladni?y=50.1023000&x=14.3568000&z={zoom}",
                                             cookies=cookies))
        MapyCZServer.__setCookies(cookies,
                                requests.get(
                                    f"https://login.mapy.cz/api/v1/user/badge?service=mapy&v=3.0&_={random():.17f}",
                                    cookies=cookies))
        sessionId = requests.post("https://pro.mapy.cz/share-position/login",
                                  json={"deviceId": str(uuid.uuid4()), "userName": "Anonym"},
                                  cookies=cookies).json()["sessionId"]
        cookies["sds"] = sessionId
        cookies["szncmpone"] = "0"
        MapyCZServer.__setCookies(cookies,
                                requests.post("https://h.seznam.cz/hit",
                                              json={"initiator": "ssp", "action": "event", "service": "mapy",
                                                    "lsid": "", "id": "17033487893610.7685192582670146",
                                                    "version": "1.0", "rus_id": "", "said": "", "login_status": "",
                                                    "pvid": "", "spa": False,
                                                    "url": f"https://en.mapy.cz/zakladni?y=50.1023000&x=14.3568000&z={zoom}",
                                                    "lses": 1703348561371, "ab": "", "serviceVariant": "",
                                                    "premium": "", "ptitle": "Basic • Mapy.cz - in English language",
                                                    "data": {"type": "regular", "action": "spenttime", "time": 20}},
                                              headers={"X-Client-Id": "dot-small", "X-Client-Version": "2.106.0",
                                                       "Referer": "https://en.mapy.cz/",
                                                       "Origin": "https://en.mapy.cz/"}))
        print("Cookies:")
        for name, value in cookies.items():
            print(f"     {name}={value}")
        # Needed cookies:
        # szncsr=1703338278; - Yes
        # last-redirect=1; - Yes
        # User-Id=1311514780bb904b; - Yes
        # sds=00b66f65-24a0-423a-a0b3-74bef0fddf0a; - Yes
        # lps=eyJfZnJlc2giOmZhbHNlLCJfcGVybWFuZW50Ijp0cnVlfQ.ZYbvvg.0lxkiBlJp1vZ14DFeamD32lZnOQ; - Yes
        # euconsent-v2=CP3PV4AP3PV4AD3ACCENAgEgAAAAAEPgAATIAAAQugRQAKAAsACoAFwAQAAyABoAEQAI4ATAAqgBbADEAH4AQkAiACJAEcAJwAZYAzQB3AD9AIQARYAuoBtAE2gKkAWoAtwBeYDBAGSANTAhcAAA.YAAAAAAAAAAA;
        # szncmpone=0 - Yes

        # Really needed cookies:
        # last-redirect=1; - Yes
        # User-Id=d3975a2768306836; - Yes
        # cmprefreshcount=0|897uggv46a;
        # lps=eyJfZnJlc2giOmZhbHNlLCJfcGVybWFuZW50Ijp0cnVlfQ.ZYb4Kw.dDl5fvbIHZnfnnP8t3ez6hvM2_c
        r = requests.get(targetUri, cookies=cookies, headers={"Referrer": "https://en.mapy.cz/"})
        assert r.status_code == 200, f"Bad status code ({r.status_code}) - scrape failed"
        return r.content"""

    def __scrapeAroundWorker(self):
        while True:
            # Wait, so the CPU usage doesn't go to 100%
            # sTime = time.time()
            self.__scrapeAroundWorkerWaiter.wait()
            # print(time.time() - sTime)
            # TODO Make sure there isn't a collision between the multiple running threads
            #  (len() > 0, but at pop(), len() = 0)
            if len(self.__scrapeAroundArgs) == 0:
                # print("WAIT")
                continue
            if len(self.__scrapeAroundArgs) > 10:  # Discard "outdated" requests
                self.__scrapeAroundArgs = self.__scrapeAroundArgs[-10:]
            args = self.__scrapeAroundArgs.pop()  # Get the most "fresh" request
            self.__scrapeAround(*args)

    def __scrapeAround(self, x: int, y: int, zoom: int, tileSize: str, mapSet: MapSet, lang: str):
        SCRAPING_RADIUS = 2
        for deltaX in range(-SCRAPING_RADIUS, SCRAPING_RADIUS + 1):
            for deltaY in range(-SCRAPING_RADIUS, SCRAPING_RADIUS + 1):
                if deltaX == 0 and deltaY == 0:
                    continue  # This is the tile we already scraped
                try:
                    # canScrapeAround=False - if not, it will repeat infinitely
                    self.__scrape(x + deltaX, y + deltaY, zoom, tileSize, mapSet, lang,
                                  canScrapeAround=False)
                except requests.exceptions.SSLError:
                    pass  # EOF occurred in violation of protocol - IDK why
        # print("Scraped around.")

    def __storeToCache(self, x: int, y: int, zoom: int, tileSize: str, mapSet: MapSet, lang: str,
                       data: bytes):
        if self.__cachePath is None:
            return
        self.__cacheSizeLimiterWaiter.release()
        with open(self.__getCacheFilePath(x, y, zoom, tileSize, mapSet, lang), "wb+") as f:
            f.write(data)

    def __obtainFromCache(self, x: int, y: int, zoom: int, tileSize: str, mapSet: MapSet,
                          lang: str) -> bytes | None:
        if self.__cachePath is None:
            return None
        path = self.__getCacheFilePath(x, y, zoom, tileSize, mapSet, lang)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    def __cleanExcessCacheItems(self):
        while True:
            self.__cacheSizeLimiterWaiter.wait()
            if self.__cachePath is None:
                continue
            files: dict[str, float] = {}  # File name: file last edited
            for dirEntry in os.scandir(self.__cachePath):
                if dirEntry.is_dir():
                    continue
                try:
                    theTime = dirEntry.stat().st_birthtime
                except AttributeError:
                    theTime = dirEntry.stat().st_mtime
                files[dirEntry.name] = theTime
            fileNames: list[str] = list(files.keys())
            fileNames.sort(key=lambda fn: round(files[fn]), reverse=True)
            # Now, fileNames are sorted by their age, newest first, oldest last
            if len(fileNames) < self.maxCacheSize - 1:
                return
            filesToDelete = fileNames[self.maxCacheSize - 1:]
            for file in filesToDelete:
                path = os.path.join(self.__cachePath, file)
                if not os.path.exists(path):
                    return
                os.remove(path)

    def __getCacheKey(self, x: int, y: int, zoom: int, tileSize: str, mapSet: MapSet,
                      lang: str) -> str:
        if zoom <= 6:
            return f"{x}_{y}_{zoom}_{tileSize}_{mapSet.value}_{lang}.png"
        return f"{x}_{y}_{zoom}_{tileSize}_{mapSet.value}.png"

    def __getCacheFilePath(self, x: int, y: int, zoom: int, tileSize: str, mapSet: MapSet,
                           lang: str) -> str:
        return os.path.join(self.__cachePath,
                            self.__getCacheKey(x, y, zoom, tileSize, mapSet, lang))

    @staticmethod
    def __setCookies(jar: RequestsCookieJar, response: requests.Response):
        if response.status_code != 200:
            print(response.status_code)
            print(response)
            print(response.text)
        assert response.status_code == 200
        for key, val in response.headers.lower_items():
            if key != "set-cookie":
                continue
            cookie = val.split(";", maxsplit=1)[0]
            name, content = cookie.split("=", maxsplit=1)
            jar[name] = content

    @staticmethod
    def __getUsageHTMLTemplate() -> bytes:
        if MapyCZServer.usageHTMLTemplate is not None:
            return MapyCZServer.usageHTMLTemplate
        with open(os.path.join(os.path.dirname(__file__), "MapyCZServerUsage.html"), "rb") as f:
            MapyCZServer.usageHTMLTemplate = f.read()
        return MapyCZServer.usageHTMLTemplate
