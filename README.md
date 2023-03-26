# anime-autodownloader
A package for automatically download animes. For now supported websites are
- AnimeUnity: https://animeunity.tv

## Installation
### From source code
- You need first to install poetry https://python-poetry.org/docs/#installation
- Then clone this repository, go inside it and type the command 
```
poetry install
```

## Usage

```python
import logging
from pathlib import Path
from animedownloader import configure_logger, getNavigator, getSupportedSites, Downloader

loglevel = logging.INFO
logger = logging.getLogger()
configure_logger(logger, loglevel, logfile="anime_download.log")

nav = getNavigator("AnimeUnity", "https://www.animeunity.tv/anime/2791-jujutsu-kaisen")

logger.info("start")
output_dir = Path.home() / "Downloads"

nav.visitBaseUrl()
urls = nav.collectAllDownloadUrls()

dw = Downloader(num_workers=5, output_dir=output_dir)
dw.download_files(urls, timeout=5400, blocking=True)
```