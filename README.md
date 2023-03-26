# anime-autodownloader
A package for automatically download animes. For now supported websites are
- AnimeUnity: https://animeunity.tv

## Dependencies
### ffmpeg
This package depends on `ffprobe` command, which is used to verify video integrity after the download of the given video has finished. This command is part of the `ffmpeg` library. In order to install it, please see [here](https://ffmpeg.org/download.html)
### Google chrome
This package works automating browser actions on the website designated for downloading the contents. At the moment of writing, only Google Chrome browser is supported, and this means that Chrome must be installed on your computer.

## Installation
To install from PyPI simple type
```
pip install anime-autodownloader
```

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
from anime_autodownloader import configure_logger, getNavigator, getSupportedSites, Downloader

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
