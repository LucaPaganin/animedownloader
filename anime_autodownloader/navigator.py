from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging, time, traceback

logger = logging.getLogger(__name__)

class AnimeUnityNavigator:
    def __init__(self, baseurl: str) -> None:
        self.baseurl = baseurl
        self.mainwindow = None
    
    def collectAllDownloadUrls(self, sleeptime=1):
        navbtns = self.driver.find_elements(By.XPATH, f"//*[@id=\"episode-nav\"]/button")
        urls = []
        if navbtns:
            for navbtn in navbtns:
                self.closeAd()
                self.clickElement(navbtn)
                urls.extend(self._retrieveDownloadUrls(sleeptime=sleeptime))
                time.sleep(1)
        else:
            urls.extend(self._retrieveDownloadUrls(sleeptime=sleeptime))
        return urls
    
    def _retrieveDownloadUrls(self, sleeptime=0.5):
        elems = self.driver.find_elements(By.CLASS_NAME, "episode-item")
        urls = []
        for i, el in enumerate(elems):
            logger.info(f"{i} - {el.text}")
            self.clickElement(el)
            time.sleep(sleeptime)
            a_elems = self.driver.find_elements(By.CLASS_NAME, "plyr__controls__item")
            dwn_a = [a for a in a_elems if a.accessible_name == "Download"][0]
            link = dwn_a.get_attribute('href')
            logger.info(link)
            urls.append(link)
        return urls
    
    def visitBaseUrl(self):
        self.driver = webdriver.Chrome()
        self.driver.get(self.baseurl)
        self.mainwindow = self.driver.window_handles[0]
        self.closeAd()
    
    def clickElement(self, element, timeout=-1):
        adclosed = False
        t0 = time.time()
        while not adclosed:
            try:
                element.click()
                adclosed = True
            except ElementClickInterceptedException:
                if timeout > 0 and (time.time() - t0) > timeout:
                    raise TimeoutError(f"Timed out while trying to click on element {element.text}")
                self.closeAd()
                continue
    
    def closeAd(self, nretry=5, sleeptime=10):
        # Wait up to 10 seconds for the iframe to be available
        for i in range(nretry):
            try:
                logger.info("Waiting to close ads")
                wait = WebDriverWait(self.driver, sleeptime)
                iframe = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'iframe[style*="position: fixed"]')
                    )
                )
                self.driver.switch_to.frame(iframe)
                closebtn = [
                    el for el in self.driver.find_elements(By.TAG_NAME, "span")
                    if el.text == "Chiudere"
                ][0]
                closebtn.click()
                logger.info("Closed ad")
                time.sleep(1)
                self.closeNonMainWindows()
            except TimeoutException:
                break
            except BaseException as e:
                logger.info(traceback.format_exc())
                time.sleep(sleeptime)
            else:
                break
    
    def closeNonMainWindows(self):
        logger.info("Closing non-main windows")
        if len(self.driver.window_handles) > 1:
            for w in self.driver.window_handles:
                if w != self.mainwindow:
                    self.driver.switch_to.window(w)
                    self.driver.close()
            self.driver.switch_to.window(self.mainwindow)