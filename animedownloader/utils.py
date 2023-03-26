import subprocess as sp
from pathlib import Path
import re, time
from queue import Queue

epno_regex = re.compile(r"(?:[eE][pP][_\-])(\d+)(?:-\d+)?")

def parse_ep_number(filename):
    match = epno_regex.search(Path(filename).stem)
    if not match:
        return None
    return int(match.groups()[0])

def check_video_integrity(videopath, debug=False):
    if not Path(videopath).is_file():
        raise FileNotFoundError(videopath)
    p = sp.run(f"ffprobe -v error {videopath}", 
               shell=True, text=True, 
               stderr=sp.PIPE, stdout=sp.PIPE)
    err = p.stderr.strip()
    if debug:
        print(err)
    return len(err) == 0, err

class TimeoutQueue(Queue):
    def join_with_timeout(self, timeout=None):
        self.all_tasks_done.acquire()
        try:
            if timeout is None:
                while self.unfinished_tasks:
                    self.all_tasks_done.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a positive number")
            else:
                endtime = time.time() + timeout
                while self.unfinished_tasks:
                    remaining = endtime - time.time()
                    if remaining <= 0.0:
                        raise TimeoutError
                    self.all_tasks_done.wait(remaining)
        finally:
            self.all_tasks_done.release()