from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

class Browser:
    def __init__(self) -> None:
        # http://browser:4444/wd/hub this domain comes from docker compose service name
        self.options = self.browser_options()
        BROWSER_URL = 'http://browser:4444/wd/hub'
        self.driver = webdriver.Remote(command_executor=BROWSER_URL, options=self.options)
        self.driver.set_page_load_timeout(60)
        self.wait = self.browser_wait()

    def browser_options(self):
        options = webdriver.ChromeOptions()
        options.page_load_strategy = 'normal'
        options.add_argument("--start-maximized")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        # Disable webdriver flags
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Additional stealth options
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)

        # Set user agent
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        return options

    def full_screen(self) -> None:
        self.driver.set_window_size(1, 1)
        self.driver.set_window_position(2000, 2000)
        return

    def browser_wait(self):
        return WebDriverWait(self.driver, 30)

    def hide_webdriver(self):
        """Inject script to hide webdriver property"""
        try:
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            print(f"Warning: Failed to hide webdriver: {e}")