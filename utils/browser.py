from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

class Browser:
    def __init__(self) -> None:
        # http://browser:4444/wd/hub this domain comes from docker compose service name
        self.options = self.browser_options()
        BROWSER_URL = 'http://browser:4444/wd/hub'
        self.driver = webdriver.Remote(command_executor=BROWSER_URL, options=self.options)  
        # self.driver = webdriver.Chrome()
        self.wait = self.browser_wait()
        
    def browser_options(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-extensions")

        # Disable webdriver flags or you will be easily detectable
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-blink-features=AutomationControlled")
        return options

    def full_screen(self) -> None:
        self.driver.set_window_size(1, 1)
        self.driver.set_window_position(2000, 2000)
        return

    def browser_wait(self):    
        return WebDriverWait(self.driver, 30)