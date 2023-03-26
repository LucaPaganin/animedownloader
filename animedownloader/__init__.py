__version__ = "0.0.1"

from .navigator import AnimeUnityNavigator
from .downloader import Downloader
from .utils import configure_logger

SUPPORTED_WEBSITES = {
    "AnimeUnity": {
        "url": "https://animeunity.tv",
        "navclass": AnimeUnityNavigator
    }
}

def getSupportedSites():
    return {k: v["url"] for k, v in SUPPORTED_WEBSITES.items()}

def getNavigator(website_key, baseurl):
    navclass = SUPPORTED_WEBSITES[website_key]["navclass"]
    return navclass(baseurl)
