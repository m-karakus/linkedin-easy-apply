from __future__ import annotations
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import yaml
import pandas as pd
import numpy as np
np.set_printoptions(suppress=True)
from bs4 import BeautifulSoup

import os 
import re
import time 
import csv
import random
import platform
import logging
from datetime import datetime, timedelta
import itertools

os.chdir(os.path.dirname(os.path.abspath(__file__)))
from utils import Logger, log_container, Browser

log = Logger()
browser = Browser()

class EasyApplyBot:
    def __init__(
        self,
        username,
        password,
        positions,
        locations,
        browser,
        blacklist=[],
        blackListTitles=[],
    ) -> None:

        log.info("Welcome to Easy Apply Bot")

        self.filename = './volumes/output.csv'
        self.appliedJobIDs = self.get_previous_ids(self.filename)
        self.blacklist = blacklist
        self.browser = browser
        self.driver = browser.driver
        self.blackListTitles = blackListTitles
        self.start_linkedin(username, password)
        self.positions = positions
        self.locations = locations
        self.base_url = "https://www.linkedin.com/jobs/search/?f_LF=f_AL&f_WT=2&keywords="
    @log_container
    def get_previous_ids(self,file_path):
        try:
            df = pd.read_csv(
                file_path,
                names=['timestamp', 'job_id', 'position', 'location', 'job', 'company', 'attempted', 'result'],
                parse_dates=['timestamp'], 
            )
            df = df[df['timestamp'] > (datetime.now() - timedelta(days=12))]
            previous_ids = np.unique(df.job_id.values)
        except:
            previous_ids = np.array([], dtype='i')
        return previous_ids
    
    @log_container
    def start_linkedin(self, username, password) -> None:
        log.info("Logging in.....Please wait :)  ")
        self.driver.get("https://www.linkedin.com/login?trk=guest_homepage-basic_nav-header-signin")
        self.browser.hide_webdriver()

        try:
            # Wait for page to fully stabilize
            time.sleep(15)

            log.debug(f"Current URL: {self.driver.current_url}")
            log.debug(f"Page title: {self.driver.title}")

            # Check for challenge/checkpoint
            if "challenge" in self.driver.current_url or "checkpoint" in self.driver.current_url:
                log.warning("LinkedIn challenge/checkpoint detected!")
                log.info("Waiting 60 seconds for manual intervention...")
                time.sleep(60)

            # Debug: check what inputs exist on the page via JS
            input_info = self.driver.execute_script("""
                const inputs = document.querySelectorAll('input');
                return Array.from(inputs).map(i => ({
                    type: i.type || 'none',
                    name: i.name || 'none',
                    id: i.id || 'none',
                    autocomplete: i.autocomplete || 'none',
                    placeholder: i.placeholder || 'none',
                    class: i.className || 'none',
                    visible: i.offsetParent !== null
                }));
            """)
            log.debug(f"Input fields on page: {input_info}")

            # Find username field — try multiple strategies
            # NOTE: LinkedIn duplicates fields (hidden + visible).
            # We must find the VISIBLE one, not the first match.
            user_field = None
            username_strategies = [
                (By.CSS_SELECTOR, "input[autocomplete='username']"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input#username"),
                (By.CSS_SELECTOR, "input[name='session_key']"),
                (By.XPATH, "//input[@type='email' or @type='text']"),
                (By.XPATH, "//form//input[contains(@id, 'username') or contains(@id, 'email')]"),
            ]

            for by, selector in username_strategies:
                try:
                    # Wait for at least one element to be present
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    # Find ALL matches, then pick the first visible + enabled one
                    elements = self.driver.find_elements(by, selector)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            user_field = el
                            log.info(f"Found visible username field via: ({by}, {selector})")
                            break
                    if user_field:
                        break
                except:
                    continue

            # If still not found, try JavaScript injection of credentials
            if not user_field:
                log.warning("Username field not found via DOM — trying JS injection")
                # Check if credentials can be set via React state or direct form manipulation
                has_form = self.driver.execute_script("""
                    const form = document.querySelector('form');
                    return form ? form.outerHTML.substring(0, 500) : 'no form found';
                """)
                log.debug(f"Form check: {has_form}")
                # Try to set values directly via JS on any visible email/username input
                user_field = self.driver.execute_script("""
                    const inputs = document.querySelectorAll('input');
                    for (const inp of inputs) {
                        const t = (inp.type || '').toLowerCase();
                        const n = (inp.name || '').toLowerCase();
                        const id = (inp.id || '').toLowerCase();
                        if (t === 'email' || t === 'text' || n.includes('email') || n.includes('user') || n === 'session_key' || id.includes('email') || id.includes('user')) {
                            inp.focus();
                            inp.value = arguments[0];
                            inp.dispatchEvent(new Event('input', {bubbles: true}));
                            inp.dispatchEvent(new Event('change', {bubbles: true}));
                            return inp;
                        }
                    }
                    return null;
                """, username)

                if user_field:
                    log.info("Username field found and filled via JS")
                    # Convert the JS element to a Selenium WebElement
                    user_field = self.driver.find_element(By.XPATH, f"//input[@value='{username[:20]}']")

            if not user_field:
                log.error("Could not find username field. Full page title: " + self.driver.title)
                log.error(f"Page URL: {self.driver.current_url}")
                page_src = self.driver.page_source[:3000]
                log.error(f"Page source (first 3000 chars): {page_src}")
                raise Exception("Username field not found")

            # Find password field — same hidden/visible duplication issue
            pw_field = None
            password_strategies = [
                (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
                (By.CSS_SELECTOR, "input[type='password']"),
                (By.CSS_SELECTOR, "input#password"),
                (By.CSS_SELECTOR, "input[name='session_password']"),
                (By.XPATH, "//form//input[contains(@id, 'password')]"),
            ]

            for by, selector in password_strategies:
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    elements = self.driver.find_elements(by, selector)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            pw_field = el
                            log.info(f"Found visible password field via: ({by}, {selector})")
                            break
                    if pw_field:
                        break
                except:
                    continue

            if not pw_field:
                raise Exception("Password field not found")

            # Fill credentials using send_keys (triggers React onChange)
            user_field.clear()
            for char in username:
                user_field.send_keys(char)
                time.sleep(random.uniform(0.01, 0.03))
            time.sleep(random.uniform(1, 2))
            pw_field.clear()
            for char in password:
                pw_field.send_keys(char)
                time.sleep(random.uniform(0.01, 0.03))
            time.sleep(random.uniform(0.5, 1))

            # Debug: check available buttons on the page (before trying selectors)
            buttons_info = self.driver.execute_script("""
                const btns = document.querySelectorAll('button');
                return Array.from(btns).map(b => ({
                    text: (b.textContent || '').trim().substring(0, 50),
                    type: b.type || 'none',
                    class: (b.className || '').substring(0, 60),
                    id: b.id || 'none',
                    visible: b.offsetParent !== null,
                    enabled: !b.disabled
                }));
            """)
            log.debug(f"Buttons on page: {buttons_info}")

            # Find visible login button via JavaScript (avoids XPath text() quirks)
            login_button = self.driver.execute_script("""
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    const text = (btn.textContent || '').trim();
                    if (btn.offsetParent !== null && !btn.disabled &&
                        (text.includes('Oturum') || text.includes('Sign in') || text.includes('Giri'))) {
                        return btn;
                    }
                }
                return null;
            """)

            if login_button:
                log.info(f"Found visible login button via JS")
                login_button.click()
            else:
                log.info("No JS-visible login button — trying form submit fallback")
                submitted = self.driver.execute_script("""
                    // Try harder: click any visible button with sign-in text
                    const btns = document.querySelectorAll('button');
                    for (const btn of btns) {
                        const text = (btn.textContent || '').trim();
                        if (btn.offsetParent !== null && !btn.disabled &&
                            (text.includes('Oturum') || text.includes('Sign in') || text.includes('Giri'))) {
                            btn.click();
                            return 'clicked: ' + text;
                        }
                    }
                    // Fallback to form submit
                    const form = document.querySelector('form');
                    if (form) {
                        form.submit();
                        return 'form.submit()';
                    }
                    return 'no action taken';
                """)
                log.info(f"JS submission result: {submitted}")

            # Wait for login to complete (up to 60s)
            try:
                WebDriverWait(self.driver, 60).until(
                    lambda d: "feed" in d.current_url or "jobs" in d.current_url
                    or "checkpoint" in d.current_url or "challenge" in d.current_url
                )
            except TimeoutException:
                log.warning(f"Login redirect timeout. Current URL: {self.driver.current_url}")
                log.warning(f"Page title: {self.driver.title}")
                # Check if we're on the same login page or somewhere else
                if "login" in self.driver.current_url:
                    log.error("Still on login page — login may have failed")
                    raise Exception("Login failed - still on login page after submission")

            # Handle checkpoint/challenge
            if "checkpoint" in self.driver.current_url or "challenge" in self.driver.current_url:
                log.warning("LinkedIn checkpoint/challenge detected. Please solve manually in browser.")
                log.info("Waiting 60 seconds for manual intervention...")
                time.sleep(60)
                WebDriverWait(self.driver, 30).until(
                    lambda d: "feed" in d.current_url or "jobs" in d.current_url
                )

            time.sleep(5)
            log.info("Login successful!")
        except Exception as e:
            log.error(f"Login failed: {e}")
            log.error(f"Current URL: {self.driver.current_url}")
            log.error(f"Page title: {self.driver.title}")
            raise e

    @log_container
    def start_apply(self) -> None:
        self.browser.full_screen()
        combinations = tuple(itertools.product(self.locations ,self.positions))
        
        for i in combinations:
            location = i[0]
            position = i[1]
            log.info(f"Applying to {position}:{location}")
            location = "&location=" + location
            self.applications_loop(position, location)
    
    @log_container
    def get_job_ids(self):
        log.debug(f"Search page URL: {self.driver.current_url}")

        # Debug: check what job card elements exist on the page
        card_debug = self.driver.execute_script("""
            const cards = document.querySelectorAll('[data-entity-urn], .job-search-card, [class*="job-card"]');
            return Array.from(cards).map(function(c) {
                return {
                    tag: c.tagName,
                    cls: (typeof c.className === 'string' ? c.className : '').substring(0, 80),
                    entity_urn: c.getAttribute('data-entity-urn') || 'none'
                };
            });
        """)
        log.debug(f"Job cards found by JS: {card_debug}")
        # LinkedIn displays the search results in a scrollable <div> on the left side, we have to scroll to its bottom
        # Try multiple possible selectors for the job results container
        scrollresults = None
        for selector in [
            "jobs-search__results-list",
            "jobs-search-results-list",
            "scaffold-layout__list-container",
            "jobs-search-results__list"
        ]:
            try:
                scrollresults = self.driver.find_element(By.CLASS_NAME, selector)
                log.info(f"Found job container by class: {selector}")
                break
            except:
                continue
        
        if not scrollresults:
            # Try xpath
            try:
                scrollresults = self.driver.find_element(By.XPATH, "//ul[contains(@class, 'jobs-search') or contains(@class, 'scaffold-layout__list')]")
                log.info("Found job container by XPath")
            except:
                log.info("Could not find job results container")
                return 0, np.array([], dtype='i')

        # Selenium only detects visible elements; if we scroll to the bottom too fast, only 8-9 results will be loaded into IDs list
        for i in range(300, 5000, 80):
            self.driver.execute_script("arguments[0].scrollTo(0, {})".format(i), scrollresults)
            time.sleep(0.05)

        # Scroll back to top to make sure all cards are rendered
        self.driver.execute_script("arguments[0].scrollTo(0, 0)", scrollresults)
        time.sleep(0.5)

        # Get job card elements using multiple selector strategies
        links = []

        # Strategy 1: job-card-list divs (current LinkedIn)
        card_strategies = [
            (By.XPATH, '//div[contains(@class, "job-card-list")]'),
            (By.XPATH, '//div[contains(@class, "job-search-card")]'),
            (By.XPATH, '//div[@data-entity-urn]'),
            (By.XPATH, '//li[contains(@class, "job-card-search")]'),
            (By.XPATH, '//a[contains(@class, "job-card-container__link")]'),
        ]

        for by, selector in card_strategies:
            links = self.driver.find_elements(by, selector)
            if links:
                log.info(f"Found {len(links)} job cards via: ({by}, {selector})")
                break

        if len(links) == 0:
            log.info("No links found")

        ids = np.array([], dtype='i')
        for link in links:
            try:
                job_id = None

                # Try data-entity-urn first
                entity_urn = link.get_attribute("data-entity-urn")
                if entity_urn:
                    job_id = int(entity_urn.split(":")[-1])

                # Try href-based ID extraction from the card itself
                if not job_id:
                    href = link.get_attribute("href")
                    if href:
                        match = re.search(r'/jobs/view/(\d+)', href)
                        if match:
                            job_id = int(match.group(1))

                # Try finding an <a> child with href
                if not job_id:
                    links_in_card = link.find_elements(By.XPATH, './/a[contains(@href, "/jobs/view/")]')
                    for a in links_in_card:
                        href = a.get_attribute("href")
                        match = re.search(r'/jobs/view/(\d+)', href)
                        if match:
                            job_id = int(match.group(1))
                            break

                # Try getting job ID from currentJobId in URL (if we're already on a job detail)
                if not job_id:
                    try:
                        current_url = self.driver.current_url
                        match = re.search(r'currentJobId=(\d+)', current_url)
                        if match:
                            job_id = int(match.group(1))
                    except:
                        pass

                # Try any link inside card that contains a number pattern
                if not job_id:
                    all_links = link.find_elements(By.XPATH, './/a')
                    for a in all_links:
                        href = a.get_attribute("href") or ''
                        match = re.search(r'/jobs/(\d+)', href)
                        if match:
                            job_id = int(match.group(1))
                            break

                if not job_id:
                    continue

                # Check if company is not in blacklist
                company_name = ""
                try:
                    company_selectors = [
                        './/h4[contains(@class, "base-search-card__subtitle")]',
                        './/span[contains(@class, "job-card-container__primary-description")]',
                        './/span[contains(@class, "job-card-list__company-name")]',
                        './/a[contains(@class, "job-card-container__company-name")]',
                        './/*[contains(@class, "job-card-list__entity-lockup")]//span',
                    ]
                    for cs in company_selectors:
                        company_elems = link.find_elements(By.XPATH, cs)
                        if company_elems:
                            company_name = company_elems[0].text.strip()
                            break
                except:
                    pass

                if company_name and company_name not in self.blacklist:
                    ids = np.append(ids, job_id)
                elif not company_name:
                    ids = np.append(ids, job_id)
            except Exception:
                continue
        
        # remove already applied jobs
        before = len(ids)
        available_ids = ids[~np.isin(ids, self.appliedJobIDs)]
        after = len(available_ids)

        return len(ids), available_ids

    @log_container
    def applications_loop(self, position, location):
        count_application = 0
        count_job = 0
        jobs_per_page = 0

        self.driver.set_window_position(1, 1)
        self.driver.maximize_window()
        self.driver, _ = self.next_jobs_page(position, location, jobs_per_page)
        log.info("Looking for jobs.. Please wait..")

        try:
            # sleep to make sure everything loads, add random to make us look human.
            randoTime = random.uniform(3.5, 4.9)
            log.debug(f"Sleeping for {round(randoTime, 1)}")
            time.sleep(randoTime)
            self.load_page(sleep=1)

            ids = 0
            job_ids = np.array([], dtype='i')

            for i  in range(25,501,25):
                try:
                    count, available_ids = self.get_job_ids()
                except:
                    count = 0
                    available_ids = np.array([], dtype='i')
                
                job_ids = np.unique(np.append(job_ids, available_ids))
                # it assumed that 25 jobs are listed in the results window
                if count < 25:
                    break
                else:
                    self.driver, jobs_per_page = self.next_jobs_page(position,location,i)
                    randoTime = random.uniform(3.5, 4.9)
            
            total_job = len(job_ids)
            # loop over ids to apply
            for i, job_id in enumerate(job_ids):
                process = round(i/total_job,2) * 100
                log.info(f"Process: {i}/{total_job}, %{process}")
                self.get_job_page(job_id)

                # get easy apply button
                button = self.get_easy_apply_button()

                if button is not False:
                    if any(word in self.driver.title for word in self.blackListTitles):
                        log.info(f"Skipping: {job_id}, Position {i} : {self.driver.title}, blacklisted.")
                        result = False
                    else:
                        log.info(f"Trying to apply: {job_id}, Position {i} : {self.driver.title}")
                        button.click()
                        time.sleep(3)
                        result = self.send_resume(job_id)
                        count_application += 1
                else:
                    log.info(f"Skipping: {job_id}, Position {i} : {self.driver.title}, EasyApply Button Not found.")
                    result = False

                self.write_to_file(button, job_id, position, location, self.driver.title, result)

                # sleep every 20 applications
                # if count_application != 0 and count_application % 20 == 0:
                #     sleepTime: int = random.randint(500, 900)
                #     log.info(f"""Time for a nap - see you in:{int(sleepTime / 60)} min""")
                #     time.sleep(sleepTime)

        except Exception as e:
            log.error(e)
            raise e

    @log_container
    def write_to_file(self, button, job_id, position, location, browserTitle, result) -> None:
        def re_extract(text, pattern):
            target = re.search(pattern, text)
            if target:
                target = target.group(1)
            return target

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        attempted = False if button == False else True
        job = str(re_extract(browserTitle.split(' | ')[0], r"\(?\)\)?\s?(\w.*)")) 
        company = re_extract(browserTitle.split(' | ')[1], r"(\w.*)")

        toWrite = [timestamp, job_id, position, location, job, company, attempted, result]
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        with open(self.filename, 'a') as f:
            writer = csv.writer(f)
            writer.writerow(toWrite)

    @log_container
    def get_job_page(self, job_id):
        job = 'https://www.linkedin.com/jobs/view/' + str(job_id)
        self.driver.get(job)
        self.job_page = self.load_page(sleep=0.5)
        return self.job_page

    @log_container
    def get_easy_apply_button(self):
        try:
            selectors = [
                "//button[contains(@class, 'jobs-apply-button')]",
                "//button[@aria-label='Easy Apply']",
                "//button[contains(., 'Easy Apply')]",
                "//button[contains(@class, 'jobs-easy-apply-button')]",
                "//span[text()='Easy Apply']/ancestor::button",
                "//span[text()='Easy Apply']/ancestor::a",
                "//a[contains(., 'Easy Apply')]",
                "//div[contains(@class, 'apply-button')]//button",
                "//div[contains(@class, 'jobs-apply-button')]//button",
                "//button[@data-easy-apply]",
            ]

            for selector in selectors:
                buttons = self.driver.find_elements(By.XPATH, selector)
                if buttons:
                    for btn in buttons:
                        try:
                            if btn.is_displayed() and btn.is_enabled():
                                log.info(f"Found Easy Apply button: {selector}")
                                return btn
                        except:
                            continue

            # Final fallback: any element with "Easy Apply" text
            fallback = self.driver.find_elements(By.XPATH, "//*[text()='Easy Apply']")
            for el in fallback:
                try:
                    if el.is_displayed():
                        log.info("Found Easy Apply text element")
                        return el
                except:
                    continue

            log.debug("Easy Apply button not found")
            return False
        except Exception as e:
            log.debug(f"Easy Apply button search error: {e}")
            return False

    @log_container
    def send_resume(self, job_id) -> bool:
        def is_present(button_locator) -> bool:
            return len(self.driver.find_elements(button_locator[0], button_locator[1])) > 0

        try:
            time.sleep(random.uniform(1.5, 2.5))

            # Debug: log all visible buttons and modals on page
            try:
                modal_info = self.driver.execute_script("""
                    const modals = document.querySelectorAll('[role="dialog"], [role="presentation"], .artdeco-modal, .jobs-easy-apply-modal, .artdeco-completeness-state-modal');
                    return Array.from(modals).map(m => ({
                        role: m.getAttribute('role'),
                        classes: m.className.substring(0,100),
                        visible: m.offsetParent !== null,
                        display: getComputedStyle(m).display,
                        buttons: Array.from(m.querySelectorAll('button')).map(b => ({
                            text: b.textContent.trim().substring(0,40),
                            'aria-label': b.getAttribute('aria-label'),
                            visible: b.offsetParent !== null,
                            disabled: b.disabled,
                            classes: b.className.substring(0,60)
                        })).filter(b => b.visible)
                    })).filter(m => m.visible);
                """)
                log.debug(f"Modals: {modal_info}")
                all_buttons = self.driver.execute_script("""
                    return Array.from(document.querySelectorAll('button')).map(b => ({
                        text: b.textContent.trim().substring(0,50),
                        'aria-label': b.getAttribute('aria-label'),
                        visible: b.offsetParent !== null,
                        disabled: b.disabled,
                        id: b.id || 'none',
                        classes: b.className.substring(0,80)
                    })).filter(b => b.visible);
                """)
                log.debug(f"Visible buttons: {all_buttons}")
                shadow_btns = self.driver.execute_script("""
                    const outlet = document.querySelector('#interop-outlet');
                    if (!outlet || !outlet.shadowRoot) return 'no shadow DOM';
                    const btns = outlet.shadowRoot.querySelectorAll('button:not([disabled])');
                    return Array.from(btns).map(b => ({
                        text: (b.textContent || '').trim().substring(0,40),
                        al: b.getAttribute('aria-label') || '',
                        visible: b.offsetParent !== null
                    }));
                """)
                log.debug(f"Shadow DOM buttons: {shadow_btns}")
            except Exception as e:
                log.debug(f"Debug dump error: {e}")

            # Modern LinkedIn Easy Apply button locators
            next_locater = (By.XPATH, "//button[@aria-label='Continue to next step' or @aria-label='Continue' or @aria-label='Next' or contains(@class, 'artdeco-button--primary') and contains(., 'Next')]")
            review_locater = (By.XPATH, "//button[@aria-label='Review your application' or @aria-label='Review']")
            submit_locater = (By.XPATH, "//button[@aria-label='Submit application' or @aria-label='Submit']")
            error_locator = (By.XPATH, "//p[contains(@class, 'artdeco-inline-feedback__message') or @data-test-form-element-error-message='true']")
            upload_locator = (By.XPATH, "//input[@type='file']")
            follow_locator = (By.XPATH, "//label[@for='follow-company-checkbox']")
            
            choose_resume = (By.XPATH, "//button[@aria-label='Choose Resume' or contains(., 'Choose Resume')]")
            term_agree = (By.XPATH, "//label[contains(@data-test-text-selectable-option__label, 'I Agree') or contains(., 'I agree to the')]")

            submitted = False
            max_c_time = 60 * 1
            c_time = time.time()
            
            loop_count = 0
            while time.time() - c_time < max_c_time:
                loop_count += 1
                message = "{job_id} - Application Could NOT Submitted!".format(job_id=str(job_id))

                # Debug: dump current visible buttons every 5th iteration
                if loop_count % 5 == 1:
                    try:
                        current_url = self.driver.current_url
                        log.debug(f"Loop {loop_count} URL: {current_url}")
                        all_btns = self.driver.execute_script("""
                            return Array.from(document.querySelectorAll('button')).map(b => ({
                                text: b.textContent.trim().substring(0,40),
                                al: b.getAttribute('aria-label') || '',
                                vis: b.offsetParent !== null,
                                dis: b.disabled
                            })).filter(b => b.vis && (b.text || b.al));
                        """)
                        log.debug(f"Loop {loop_count} buttons: {all_btns[:10]}")
                    except:
                        pass
                
                # Handle resume selection if needed
                if is_present(choose_resume):
                    try:
                        button = self.browser.wait.until(EC.element_to_be_clickable(choose_resume))
                        button.click()
                        time.sleep(random.uniform(1.5, 2.5))
                    except:
                        pass

                # Handle terms agreement
                if is_present(term_agree):
                    try:
                        button = self.browser.wait.until(EC.element_to_be_clickable(term_agree))
                        button.click()
                        time.sleep(random.uniform(1.5, 2.5))
                    except:
                        pass

                # Fill ONLY required form fields inside shadow DOM, skip optional and pre-filled
                try:
                    # Dump ALL visible fields for debug
                    self.driver.execute_script("""
                        const outlet = document.querySelector('#interop-outlet');
                        if (!outlet || !outlet.shadowRoot) return;
                        const root = outlet.shadowRoot;
                        function isRequired(el) { return el.hasAttribute('required') || el.getAttribute('aria-required') === 'true'; }
                        const all = root.querySelectorAll('input, select, textarea, [contenteditable], [role="combobox"]');
                        const info = Array.from(all).filter(e => e.offsetParent !== null).map(e => ({
                            t: e.tagName,
                            ty: (e.getAttribute('type') || e.getAttribute('role') || ''),
                            id: (e.id || '').slice(-50),
                            req: isRequired(e),
                            v: (e.value !== undefined ? e.value.slice(0,20) : (e.textContent||'').trim().slice(0,20)),
                        }));
                        return info;
                    """)
                    # but don't log it to avoid spam, only log non-empty ones

                    # Find all problematic fields (required but empty/invalid)
                    fields = self.driver.execute_script("""
                        const outlet = document.querySelector('#interop-outlet');
                        if (!outlet || !outlet.shadowRoot) return [];
                        const root = outlet.shadowRoot;

                        function isRequired(el) {
                            return el.hasAttribute('required') || el.getAttribute('aria-required') === 'true';
                        }

                        const results = [];

                        // ALL input-like elements: required & (empty OR number with value <= 0)
                        const allInputs = root.querySelectorAll('input:not([type="radio"]):not([type="checkbox"]):not([type="file"]), textarea, select');
                        for (const f of allInputs) {
                            if (f.offsetParent === null) continue;
                            if (!isRequired(f)) continue;
                            const type = (f.getAttribute('type') || '').toLowerCase();
                            const tag = f.tagName.toLowerCase();

                            if (tag === 'select') {
                                const val = (f.value || '').trim();
                                // Also catch selects whose value is a placeholder ("Select an option")
                                if (!val || val.toLowerCase().includes('select')) {
                                    const opts = Array.from(f.querySelectorAll('option')).filter(o => o.value && !o.disabled);
                                    // Skip the placeholder option if it's first
                                    const realOpts = opts.filter(o => !o.value.toLowerCase().includes('select'));
                                    const pick = realOpts.length > 0 ? realOpts : opts;
                                    if (pick.length > 0) {
                                        results.push({el: f, kind: 'select', id: f.id || '', options: pick.map(o => o.value)});
                                    }
                                }
                            } else if (type === 'number') {
                                const num = parseFloat(f.value);
                                if (isNaN(num) || num <= 0) {
                                    results.push({el: f, kind: 'number', id: f.id || '', val: f.value});
                                }
                            } else {
                                // text, tel, email, textarea, etc.
                                const isNumeric = (f.id || '').toLowerCase().includes('numeric') || (f.getAttribute('aria-label') || '').toLowerCase().includes('numeric');
                                if (isNumeric) {
                                    const num = parseFloat(f.value);
                                    if (isNaN(num) || num <= 0 || num > 100) {
                                        results.push({el: f, kind: 'text', id: f.id || '', placeholder: f.getAttribute('placeholder') || ''});
                                    }
                                } else if (!(f.value || '').trim()) {
                                    results.push({el: f, kind: 'text', id: f.id || '', placeholder: f.getAttribute('placeholder') || ''});
                                }
                            }
                        }

                        // Radio button groups: required & none checked
                        const groups = {};
                        const radios = root.querySelectorAll('input[type="radio"]');
                        for (const r of radios) {
                            const name = r.getAttribute('name') || '';
                            if (!groups[name]) groups[name] = {required: isRequired(r), buttons: []};
                            groups[name].buttons.push(r);
                        }
                        for (const g of Object.values(groups)) {
                            if (!g.required) continue;
                            if (g.buttons.some(r => r.checked)) continue;
                            if (g.buttons.length > 0) results.push({el: g.buttons[0], kind: 'radio', id: ''});
                        }

                        // Comboboxes: required & no selection
                        const combos = root.querySelectorAll('[role="combobox"]');
                        for (const cb of combos) {
                            if (cb.offsetParent === null) continue;
                            if (!isRequired(cb)) continue;
                            // For input elements check .value, for others check textContent
                            const isInput = cb.tagName === 'INPUT';
                            const currentVal = isInput ? (cb.value || '').trim() : (cb.textContent || '').trim();
                            if (currentVal && !currentVal.includes('Select')) continue;
                            results.push({el: cb, kind: 'combobox', id: cb.id || ''});
                        }

                        return results.map(r => ({
                            kind: r.kind,
                            id: r.id || '',
                            placeholder: r.placeholder || '',
                            options: r.options ? r.options.slice(0,3) : [],
                            val: r.val || ''
                        }));
                    """)
                    if fields:
                        log.debug(f"Problematic fields: {fields}")
                        # Debug dump field attributes for first field
                        if fields:
                            f0 = fields[0]
                            el0 = self.driver.execute_script("""
                                const el = document.querySelector('#interop-outlet')?.shadowRoot?.getElementById(arguments[0]);
                                if (!el) return null;
                                return {
                                    tag: el.tagName,
                                    type: el.getAttribute('type') || '',
                                    pattern: el.getAttribute('pattern') || '',
                                    min: el.getAttribute('min') || '',
                                    max: el.getAttribute('max') || '',
                                    step: el.getAttribute('step') || '',
                                    'aria-label': el.getAttribute('aria-label') || '',
                                    placeholder: el.getAttribute('placeholder') || '',
                                    class: (el.className || '').substring(0,80),
                                    readonly: el.readOnly,
                                    disabled: el.disabled,
                                    role: el.getAttribute('role') || '',
                                    value: el.value || '',
                                    innerText: (el.textContent || '').trim().substring(0,40)
                                };
                            """, f0.get('id', ''))
                            if el0:
                                log.debug(f"Field debug: {el0}")

                    # Fill each field
                    for f_info in fields:
                        kind = f_info.get('kind')
                        el_id = f_info.get('id', '')
                        try:
                            if kind == 'text':
                                is_num = 'numeric' in el_id.lower()
                                val = 'Remote, United States' if ('location' in el_id.lower() or 'geo' in el_id.lower()) else ('5' if is_num else '9')
                                el = self.driver.execute_script("""
                                    return document.querySelector('#interop-outlet')?.shadowRoot?.getElementById(arguments[0]);
                                """, el_id)
                                if el:
                                    self.driver.execute_script("arguments[0].focus(); arguments[0].value = '';", el)
                                    el.send_keys(val)
                                    time.sleep(0.2)
                                # Native setter backup - use Number for numeric fields
                                self.driver.execute_script("""
                                    const el = document.querySelector('#interop-outlet')?.shadowRoot?.getElementById(arguments[0]);
                                    if (!el) return;
                                    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                                    const newVal = arguments[2] ? Number(arguments[1]) : arguments[1];
                                    setter.call(el, newVal);
                                    el.dispatchEvent(new Event('input', {bubbles: true}));
                                    el.dispatchEvent(new Event('change', {bubbles: true}));
                                    el.dispatchEvent(new FocusEvent('blur', {bubbles: true}));
                                """, el_id, val, is_num)
                                log.debug(f"Filled text '{el_id}' -> '{val}' (is_num={is_num})")
                                time.sleep(0.3)
                            elif kind == 'number':
                                val = '5'
                                el = self.driver.execute_script("""
                                    return document.querySelector('#interop-outlet')?.shadowRoot?.getElementById(arguments[0]);
                                """, el_id)
                                if el:
                                    self.driver.execute_script("arguments[0].focus(); arguments[0].value = '';", el)
                                    el.send_keys(val)
                                    time.sleep(0.2)
                                self.driver.execute_script("""
                                    const el = document.querySelector('#interop-outlet')?.shadowRoot?.getElementById(arguments[0]);
                                    if (!el) return;
                                    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                                    setter.call(el, Number(arguments[1]));
                                    el.dispatchEvent(new Event('input', {bubbles: true}));
                                    el.dispatchEvent(new Event('change', {bubbles: true}));
                                    el.dispatchEvent(new FocusEvent('blur', {bubbles: true}));
                                """, el_id, val)
                                log.debug(f"Filled number '{el_id}' -> '{val}'")
                                time.sleep(0.3)
                            elif kind == 'select':
                                opts = f_info.get('options', [])
                                val = opts[0] if opts else ''
                                if val:
                                    self.driver.execute_script("""
                                        const el = document.querySelector('#interop-outlet')?.shadowRoot?.getElementById(arguments[0]);
                                        if (el) {
                                            el.value = arguments[1];
                                            el.dispatchEvent(new Event('change', {bubbles: true}));
                                            el.dispatchEvent(new Event('input', {bubbles: true}));
                                        }
                                    """, el_id, val)
                                    log.debug(f"Filled select '{el_id}' -> '{val}'")
                                time.sleep(0.3)
                            elif kind == 'radio':
                                self.driver.execute_script("""
                                    const outlet = document.querySelector('#interop-outlet');
                                    if (!outlet || !outlet.shadowRoot) return;
                                    const radios = outlet.shadowRoot.querySelectorAll('input[type="radio"]');
                                    for (const r of radios) {
                                        if (r.offsetParent !== null && !r.disabled &&
                                            (r.hasAttribute('required') || r.getAttribute('aria-required') === 'true')) {
                                            const name = r.getAttribute('name') || '';
                                            const sameName = Array.from(radios).filter(x => (x.getAttribute('name') || '') === name);
                                            if (sameName.some(x => x.checked)) break;
                                            r.click(); break;
                                        }
                                    }
                                """)
                                log.debug("Clicked first required radio")
                                time.sleep(0.3)
                            elif kind == 'combobox':
                                is_location = 'location' in el_id.lower() or 'geo' in el_id.lower()
                                if is_location:
                                    # Location typeahead: send keys + native set + blur
                                    loc_val = 'Remote, United States'
                                    el = self.driver.execute_script("""
                                        return document.querySelector('#interop-outlet')?.shadowRoot?.getElementById(arguments[0]);
                                    """, el_id)
                                    if el and el.tag_name == 'INPUT':
                                        el.clear()
                                        el.send_keys(loc_val)
                                        time.sleep(0.5)
                                    # Also set natively and dispatch events as backup
                                    self.driver.execute_script("""
                                        const el = document.querySelector('#interop-outlet')?.shadowRoot?.getElementById(arguments[0]);
                                        if (!el) return;
                                        el.value = arguments[1];
                                        el.dispatchEvent(new Event('input', {bubbles: true}));
                                        el.dispatchEvent(new Event('change', {bubbles: true}));
                                        el.dispatchEvent(new Event('blur', {bubbles: true}));
                                    """, el_id, loc_val)
                                    # Try clicking autocomplete option
                                    time.sleep(0.5)
                                    self.driver.execute_script("""
                                        const items = document.querySelectorAll('[role="option"], .artdeco-typeahead-suggestion, [data-test-typeahead-suggestion]');
                                        for (const it of items) {
                                            if (it.offsetParent !== null && !it.disabled) { it.click(); break; }
                                        }
                                    """)
                                    log.debug(f"Filled location combobox '{el_id}' -> '{loc_val}'")
                                else:
                                    # Generic combobox: click and select first option
                                    self.driver.execute_script("""
                                        const el = document.querySelector('#interop-outlet')?.shadowRoot?.getElementById(arguments[0]);
                                        if (!el) return;
                                        el.click();
                                        const opts = el.getRootNode().querySelectorAll('[role="option"], [role="menuitem"]');
                                        for (const o of opts) {
                                            if (o.offsetParent !== null && !o.disabled) { o.click(); break; }
                                        }
                                    """, el_id)
                                    log.debug(f"Filled combobox '{el_id}'")
                                time.sleep(0.5)
                        except Exception as fill_err:
                            log.debug(f"Failed to fill {kind} '{el_id}': {fill_err}")
                except Exception as e:
                    log.debug(f"Form-fill error: {e}")

                # Uncheck "Follow company" checkbox/toggle inside shadow DOM
                try:
                    self.driver.execute_script("""
                        const outlet = document.querySelector('#interop-outlet');
                        if (!outlet || !outlet.shadowRoot) return;
                        const root = outlet.shadowRoot;

                        // Try all known follow element patterns
                        // 1. Input checkbox with follow label
                        const checks = root.querySelectorAll('input[type="checkbox"]');
                        for (const c of checks) {
                            const ctx = ((c.closest('label') || c.parentElement || {}).textContent || '').toLowerCase();
                            const aria = (c.getAttribute('aria-label') || '').toLowerCase();
                            if (c.checked && (ctx.includes('follow') || aria.includes('follow'))) {
                                c.click();
                            }
                        }

                        // 2. Switch role toggles
                        const switches = root.querySelectorAll('[role="switch"]');
                        for (const s of switches) {
                            const ctx = (s.textContent || '').toLowerCase();
                            const aria = (s.getAttribute('aria-label') || '').toLowerCase();
                            if ((ctx.includes('follow') || aria.includes('follow')) && s.getAttribute('aria-checked') === 'true') {
                                s.click();
                            }
                        }

                        // 3. Any button/label that contains "follow" and is a toggle
                        const labels = root.querySelectorAll('label, button, [role="checkbox"]');
                        for (const lb of labels) {
                            const text = (lb.textContent || '').toLowerCase();
                            const aria = (lb.getAttribute('aria-label') || '').toLowerCase();
                            if (!text.includes('follow') && !aria.includes('follow')) continue;
                            const innerCheck = lb.querySelector('input[type="checkbox"], [role="checkbox"]');
                            if (innerCheck && (innerCheck.checked || innerCheck.getAttribute('aria-checked') === 'true')) {
                                innerCheck.click();
                            } else if (lb.getAttribute('aria-pressed') === 'true') {
                                lb.click();
                            }
                        }
                    """)
                except:
                    pass

                # Detect error messages on the page
                error_found = False
                try:
                    errors = self.driver.execute_script("""
                        const msgs = document.querySelectorAll('[data-test-form-element-error-message], .artdeco-inline-feedback__message, [role="alert"]');
                        const shadowMsgs = (document.querySelector('#interop-outlet') || {}).shadowRoot?.querySelectorAll('[data-test-form-element-error-message], .artdeco-inline-feedback__message, [role="alert"]') || [];
                        const all = [...msgs, ...shadowMsgs];
                        const errDetails = Array.from(all).map(e => ({
                            text: (e.textContent || '').trim(),
                            id: (e.id || '').slice(-30),
                            for: e.getAttribute('for') || e.getAttribute('data-test-error') || '',
                            parentId: (e.parentElement?.id || (e.parentElement?.closest?.('[data-test-form-element]')?.id || '')).slice(-30)
                        })).filter(e => e.text);
                        return errDetails;
                    """)
                    if errors and any(e.get('text') for e in errors):
                        log.debug(f"Error messages: {errors}")
                        error_found = True
                    # Also check the shadow DOM form validity
                    form_valid = self.driver.execute_script("""
                        const outlet = document.querySelector('#interop-outlet');
                        if (!outlet || !outlet.shadowRoot) return 'no shadow';
                        const root = outlet.shadowRoot;
                        // Expand any collapsed sections
                        root.querySelectorAll('[aria-expanded="false"], .collapsed, .jobs-easy-apply-form-section__collapsed').forEach(el => el.click());
                        const form = root.querySelector('form');
                        if (!form) return 'no form';
                        const fields = Array.from(form.querySelectorAll('input, select, textarea'));
                        const invalid = fields.filter(f => !f.validity.valid);
                        return {
                            totalFields: fields.length,
                            invalidCount: invalid.length,
                            allFields: fields.map(f => ({
                                id: (f.id||'').slice(-50),
                                value: (f.value||'').slice(0,20),
                                valid: f.validity.valid,
                                msg: f.validationMessage || ''
                            }))
                        };
                    """)
                    if isinstance(form_valid, dict) and form_valid.get('totalFields') is not None:
                        log.debug(f"Form fields: {form_valid}")
                except:
                    pass

                # Click Next or Submit button via JS (to handle shadow DOM)
                button = None
                button_labels = ['next', 'review', 'follow', 'submit']
                buttons = [next_locater, review_locater, follow_locator, submit_locater]
                
                # First try finding buttons inside shadow DOM (Easy Apply modal lives there)
                shadow_button_clicked = False
                try:
                    shadow_buttons = self.driver.execute_script("""
                        const outlet = document.querySelector('#interop-outlet');
                        if (!outlet || !outlet.shadowRoot) return [];
                        const buttons = outlet.shadowRoot.querySelectorAll('button');
                        return Array.from(buttons).map(b => ({
                            text: (b.textContent || '').trim().substring(0,40),
                            al: b.getAttribute('aria-label') || '',
                            visible: b.offsetParent !== null,
                            disabled: b.disabled
                        }));
                    """)
                    log.debug(f"Loop {loop_count}: Shadow DOM buttons: {shadow_buttons}")
                except Exception as e:
                    log.debug(f"Loop {loop_count}: Shadow DOM error: {e}")
                    shadow_buttons = []
                
                # Try JS click on shadow DOM buttons that match
                for sb in (shadow_buttons or []):
                    if sb.get('disabled'): continue
                    al = (sb.get('al', '') or '').lower()
                    text = (sb.get('text', '') or '').lower()
                    action = None
                    if 'next' in al or 'continue' in al or (al == '' and 'next' in text):
                        action = 'next'
                    elif 'review' in al:
                        action = 'review'
                    elif 'submit' in al or 'send' in al or (al == '' and ('submit' in text or 'send' in text)):
                        action = 'submit'
                    
                    if action:
                        click_result = self.driver.execute_script(f"""
                            const outlet = document.querySelector('#interop-outlet');
                            if (!outlet || !outlet.shadowRoot) return 'no shadow';
                            const btns = outlet.shadowRoot.querySelectorAll('button');
                            for (const b of btns) {{
                                const al = (b.getAttribute('aria-label') || '').toLowerCase();
                                const txt = (b.textContent || '').trim().toLowerCase();
                                if (!b.disabled && (
                                    al.includes('next') || al.includes('continue') ||
                                    al.includes('review') ||
                                    al.includes('submit') || al.includes('send')
                                )) {{
                                    b.click(); return 'clicked';
                                }}
                            }}
                            return 'no match';
                        """)
                        log.debug(f"Loop {loop_count}: Shadow DOM {action} click: {click_result}")
                        shadow_button_clicked = True
                        time.sleep(random.uniform(2, 3))
                        if action == 'submit':
                            submitted = True
                            message = "{job_id} - Application Submitted!".format(job_id=str(job_id))
                        elif action == 'review' and loop_count >= 5:
                            # After 5+ review clicks without progress, try clicking Submit directly
                            log.debug(f"Loop {loop_count}: Review stuck, trying Submit fallback")
                            self.driver.execute_script("""
                                const outlet = document.querySelector('#interop-outlet');
                                if (!outlet || !outlet.shadowRoot) return;
                                const btns = outlet.shadowRoot.querySelectorAll('button');
                                for (const b of btns) {
                                    const txt = (b.textContent || '').trim().toLowerCase();
                                    const al = (b.getAttribute('aria-label') || '').toLowerCase();
                                    if ((al.includes('submit') || txt.includes('submit')) && !b.disabled) {
                                        b.click(); return;
                                    }
                                }
                            """)
                            time.sleep(random.uniform(2, 3))
                        break
                
                # Skip selenium fallback if shadow DOM handled it
                if shadow_button_clicked and not submitted:
                    continue
                if submitted:
                    break
                
                # Fallback: try standard selenium locators
                for i, button_locator in enumerate(buttons):
                    if is_present(button_locator):
                        try:
                            button = self.browser.wait.until(EC.element_to_be_clickable(button_locator))
                            try:
                                btn_text = button.text.strip()[:30] or button.get_attribute('aria-label')[:30]
                            except:
                                btn_text = 'unknown'
                            log.debug(f"Loop {loop_count}: Found clickable {button_labels[i]} button via selenium: '{btn_text}'")
                        except:
                            continue
                    
                    if button:
                        try:
                            self.driver.execute_script("arguments[0].click();", button)
                            log.debug(f"Loop {loop_count}: JS-clicked {button_labels[i]} button: '{btn_text}'")
                            time.sleep(random.uniform(1.5, 2.5))
                            if i == 3:  # submit
                                submitted = True
                            if i != 2:  # break after next, review, submit; continue for follow
                                break
                        except Exception as click_err:
                            log.debug(f"Loop {loop_count}: Click failed on {button_labels[i]}: {click_err}")
                            pass
                
                if button is None:
                    log.debug(f"Loop {loop_count}: No buttons found, breaking")
                    break
                elif submitted:
                    message = "{job_id} - Application Submitted!".format(job_id=str(job_id))
                    break
            
            log.info(message)
            time.sleep(random.uniform(1.5, 2.5))

        except Exception as e:
            log.info(e)
            log.info("cannot apply to this job")
            raise (e)

        return submitted

    @log_container
    def load_page(self, sleep=1):
        # Scroll main window
        scroll_page = 0
        while scroll_page < 4000:
            self.driver.execute_script("window.scrollTo(0," + str(scroll_page) + " );")
            scroll_page += 200
            time.sleep(sleep)

        # Also scroll the job list container if present (LinkedIn's scrollable div)
        containers_to_try = [
            (By.CLASS_NAME, 'scaffold-layout__list-container'),
            (By.CLASS_NAME, 'scaffold-layout__list'),
            (By.CLASS_NAME, 'jobs-search-results-list'),
            (By.CLASS_NAME, 'jobs-search-results__list'),
            (By.XPATH, "//ul[contains(@class, 'jobs-search') or contains(@class, 'scaffold')]"),
        ]
        container = None
        for by, selector in containers_to_try:
            try:
                container = self.driver.find_element(by, selector)
                log.debug(f"Scroll container found: {by}, {selector}")
                break
            except:
                continue

        if container:
            for px in range(300, 5000, 80):
                self.driver.execute_script("arguments[0].scrollTo(0, {})".format(px), container)
                time.sleep(0.05)
            # Scroll back to top to trigger render of all cards
            self.driver.execute_script("arguments[0].scrollTo(0, 0)", container)
            time.sleep(0.5)

        if sleep != 1:
            self.driver.execute_script("window.scrollTo(0,0);")
            time.sleep(sleep * 3)

        page = BeautifulSoup(self.driver.page_source, "lxml")
        return page

    @log_container
    def next_jobs_page(self, position, location, jobs_per_page):

        page_num = jobs_per_page // 25
        url = self.base_url + position + location + f"&pageNum={page_num}"
        log.debug(f"Loading page URL: {url}")
        self.driver.get(url)

        self.load_page()
        return (self.driver, jobs_per_page)

    def finish_apply(self) -> None:
        self.driver.close()

def main():
    with open("config.yaml", 'r') as f:
        try:
            parameters = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise e

    assert len(parameters['positions']) > 0
    assert len(parameters['locations']) > 0
    assert parameters['username'] is not None
    assert parameters['password'] is not None

    blacklist = parameters.get('blacklist', [])
    blackListTitles = parameters.get('blackListTitles', [])

    locations = [l for l in parameters['locations'] if l != None]
    positions = [p for p in parameters['positions'] if p != None]

    bot = EasyApplyBot(
        parameters['username'],
        parameters['password'],
        blacklist=blacklist,
        blackListTitles=blackListTitles,
        positions=positions,
        locations=locations,
        browser=browser
    )
    loop = 0
    while True:
        log.info(f"Loop Started: {loop}")
        bot.start_apply()
        loop = loop + 1
        
        log.info("Loop complated. Giving 7 hours break...")
        time.sleep(60*60*7)

if __name__ == '__main__':
    main()
