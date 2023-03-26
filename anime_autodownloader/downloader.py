import logging, requests, time, threading, traceback, json
from pathlib import Path
from .utils import TimeoutQueue, parse_ep_number, check_video_integrity

logger = logging.getLogger(__name__)

class DownloaderError(Exception):
    def __init__(self, operation, status_code, message) -> None:
        self.operation = operation
        self.status_code = status_code
        self.message = message
    
    def __repr__(self) -> str:
        return f"DownloaderError in operation {self.operation}, {self.status_code}: {self.message}"
    
    def __str__(self) -> str:
        return self.__repr__()


def retry_request(nretry, retrysleep, method, url, *args, **kwargs) -> requests.Response:
    raiseerror = kwargs.pop("raiseerror", False)
    for _ in range(nretry):
        try:
            r = requests.request(method, url, *args, **kwargs)
            break
        except:
            time.sleep(retrysleep)
    if raiseerror:
        r.raise_for_status()
    return r


class Downloader(object):
    def __init__(self, num_workers=5, output_dir=".") -> None:
        self.info_download = {}
        self.lock = threading.Lock()
        self.num_workers = num_workers
        self.output_dir = Path(output_dir)
        self.progress_file = self.output_dir / "progress.json"
        self._finish_download_flag = threading.Event()
        self._emergency_stop = threading.Event()
        self.semaphore = threading.Semaphore(self.num_workers)
        self.workers = []
        self.queue = None
    
    def isDownloadFinished(self):
        return self._finish_download_flag.is_set()
    
    def _singleDownload(self, url, filename) -> requests.Response:
        logger.info(f"Downloading {filename}")
        t0 = time.time()
        try:
            # response = retry_request(nretry, retrysleep, "get", url, stream=True, raiseerror=True)
            response = requests.get(url, stream=True)
        except BaseException as e:
            status_code = None
            desc = ""
            if hasattr(e, "response"):
                status_code = e.response.status_code
                desc = e.response.text
            raise DownloaderError("_singleDownload", status_code, desc) from e
        if response.status_code != 200:
            desc = f"filename {filename}; "
            desc += response.text if len(response.text) < 100 else "response too long"
            raise DownloaderError("_download", response.status_code, desc)
        with open(filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                if self._emergency_stop.is_set():
                    break
        check, ffprobe_err = check_video_integrity(filename)
        if not check:
            raise DownloaderError("_singleDownload", response.status_code, f"Problems with file {filename}, url {url}, ffprobe stderr: {ffprobe_err}")
        logger.info(f"Finished downloading {filename}, elapsed time {time.time()-t0:.2f} s, response code: {response.status_code}")
        return response
    
    def retryDownload(self, nretry, retrysleep, url, filename):
        with self.lock:
            self.info_download[url] = {
                "status": "pending",
                "filename": str(filename)
            }
        fail = False
        response = None
        for i in range(nretry):
            try:
                logger.info(f"download attempt {i} for url {url}")
                response = self._singleDownload(url, filename)
                fail = False
                break
            except DownloaderError as e:
                fail = True
                logger.warning(f"attempt {i}, error: {e}")
            finally:
                if self._emergency_stop.is_set():
                    break
                else:
                    time.sleep(retrysleep)
        fsize = None
        status_code = response.status_code if isinstance(response, requests.Response) else None
        if Path(filename).is_file():
            fsize = Path(filename).stat().st_size
        if fail:
            logger.error(f"Problems with file {filename}, response code {status_code}, size {fsize} bytes")
        else:
            logger.info(f"File {filename} downloaded correctly, response code {status_code}, size {fsize} bytes")
        with self.lock:
            self.info_download[url]["status"] = "error" if fail else "success"
        return response, fail

    def progressFileUpdater(self):
        while not self._finish_download_flag.is_set():
            with self.lock:
                self.progress_file.write_text(json.dumps(self.info_download, indent=2))
            time.sleep(5)
    
    def downloadWorker(self):
        while not self._emergency_stop.is_set():
            # Get a link from the queue
            url = self.queue.get()
            if url is None:
                break
            # Download the file
            basename = url.split("filename=")[1]
            ep = parse_ep_number(basename)
            if ep is not None:
                basename = f"{str(ep).zfill(4)}_{basename}"
            filename = self.output_dir / basename
            if filename.is_file():
                logger.info(f"{filename} already present")
            else:
                self.semaphore.acquire()
                self.retryDownload(nretry=10, retrysleep=30, url=url, filename=filename)
                self.semaphore.release()
            # Mark the task as done
            self.queue.task_done()
    
    def emergencyStop(self):
        self._emergency_stop.set()
        self._finish_download_flag.set()
        time.sleep(3)
        self.stopWorkers()
    
    def stopWorkers(self):
        logger.info("stopping workers")
        # Stop the worker threads
        for i in range(self.num_workers):
            self.queue.put(None)
        logger.info("joining workers")
        for t in self.workers:
            t.join()
    
    def _download_files(self, urls, timeout):
        t0 = time.time()
        self.output_dir.mkdir(exist_ok=True, parents=True)
        # Create a queue of links to download
        self.queue = TimeoutQueue()
        for url in urls:
            self.queue.put(url)

        # Create worker threads
        self.workers = []
        for i in range(self.num_workers):
            t = threading.Thread(target=self.downloadWorker, daemon=True)
            t.start()
            self.workers.append(t)
        
        progth = threading.Thread(target=self.progressFileUpdater, daemon=True)
        progth.start()
        self.workers.append(progth)

        # Wait for all tasks to be completed
        try:
            self.queue.join_with_timeout(timeout=timeout)
        except TimeoutError:
            logger.warning(f"queue join timed out")
        self._finish_download_flag.set()
        self.stopWorkers()
        logger.info(f"download_files elapsed time: {time.time()-t0:.2f} s")
    
    def download_files(self, urls, timeout=7200, blocking=True):
        # Create the output directory if it doesn't exist
        if blocking:
            self._download_files(urls, timeout=timeout)
        else:
            threading.Thread(target=self._download_files, args=(urls, timeout), daemon=True).start()
