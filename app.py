from __future__ import annotations
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
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

@log_container
def get_previous_ids(file_path):
    df = pd.read_csv(
        file_path,
        header=None,
        names=['timestamp', 'job_id', 'job', 'company', 'attempted', 'result'],
        lineterminator='\n',
        encoding='utf-8'
    )

    df['timestamp'] = pd.to_datetime(df['timestamp'], format="%Y-%m-%d %H:%M:%S")
    df = df[df['timestamp'] > (datetime.now() - timedelta(days=12))]

    previous_ids = np.unique(df.job_id.values)
    return previous_ids



class EasyApplyBot:
    def __init__(
        self,
        username,
        password,
        positions,
        locations,
        blacklist=[],
        blackListTitles=[],
    ) -> None:

        log.info("Welcome to Easy Apply Bot")

        self.filename = './volumes/output.csv'
        self.appliedJobIDs = get_previous_ids(self.filename)
        self.blacklist = blacklist
        self.browser = browser.driver
        self.blackListTitles = blackListTitles
        self.start_linkedin(username, password)
        self.positions = positions
        self.locations = locations

    @log_container
    def start_linkedin(self, username, password) -> None:
        log.info("Logging in.....Please wait :)  ")
        self.browser.get("https://www.linkedin.com/login?trk=guest_homepage-basic_nav-header-signin")
        try:
            user_field = self.browser.find_element("id","username")
            pw_field = self.browser.find_element("id","password")
            login_button = self.browser.find_element("xpath",'//*[@id="organic-div"]/form/div[3]/button')
            user_field.send_keys(username)
            user_field.send_keys(Keys.TAB)
            time.sleep(2)
            pw_field.send_keys(password)
            time.sleep(2)
            login_button.click()
            time.sleep(25)
        except Exception as e:
            raise e

    @log_container
    def start_apply(self) -> None:
        browser.full_screen()
        combinations = tuple(itertools.product(self.positions, self.locations))
        for i in combinations:
            position = i[0]
            location = i[1]
            log.info(f"Applying to {position}:{location}")
            location = "&location=" + location
            self.applications_loop(position, location)
    
    def get_job_ids(self):
        # LinkedIn displays the search results in a scrollable <div> on the left side, we have to scroll to its bottom
        scrollresults = self.browser.find_element(By.CLASS_NAME,"jobs-search-results-list")

        # Selenium only detects visible elements; if we scroll to the bottom too fast, only 8-9 results will be loaded into IDs list
        for i in range(300, 3000, 100):
            self.browser.execute_script("arguments[0].scrollTo(0, {})".format(i), scrollresults)

        time.sleep(1)
        # get job links, (the following are actually the job card objects)
        links = self.browser.find_elements("xpath",'//div[@data-job-id]')

        if len(links) == 0:
            log.debug("No links found")

        ids = np.array([], dtype='i')
        # children selector is the container of the job cards on the left
        for link in links:
            children = link.find_elements("xpath",'//ul[@class="scaffold-layout__list-container"]')
            for child in children:
                if child.text not in self.blacklist:
                    temp = link.get_attribute("data-job-id")
                    job_id = int(temp.split(":")[-1])
                    ids = np.append(ids,job_id)
        
        # remove already applied jobs
        before = len(ids)
        available_ids = ids[~np.isin(ids,self.appliedJobIDs)]
        after = len(available_ids)

        return len(ids), available_ids

    @log_container
    def applications_loop(self, position, location):
        count_application = 0
        count_job = 0
        jobs_per_page = 0
        start_time = time.time()

        self.browser.set_window_position(1, 1)
        self.browser.maximize_window()
        self.browser, _ = self.next_jobs_page(position, location, jobs_per_page)
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
                count, available_ids = self.get_job_ids()
                job_ids = np.append(job_ids,available_ids)
                
                # it assumed that 25 jobs are listed in the results window
                if count < 25:
                    break
                else:
                    self.browser, jobs_per_page = self.next_jobs_page(position,location,i)
            
            # loop over ids to apply
            for i, job_id in enumerate(job_ids):
                count_job += 1
                self.get_job_page(job_id)

                # get easy apply button
                button = self.get_easy_apply_button()
                # word filter to skip positions not wanted

                if button is not False:
                    if any(word in self.browser.title for word in self.blackListTitles):
                        log.info('skipping this application, a blacklisted keyword was found in the job position')
                        string_easy = "* Contains blacklisted keyword"
                        result = False
                    else:
                        string_easy = "* has Easy Apply Button"
                        log.info("Clicking the EASY apply button")
                        button.click()
                        time.sleep(3)
                        result: bool = self.send_resume()
                        count_application += 1
                else:
                    log.info("The button does not exist.")
                    string_easy = "* Doesn't have Easy Apply Button"
                    result = False

                position_number: str = str(count_job + jobs_per_page)
                log.info(f"\nPosition {position_number}:\n {self.browser.title} \n {string_easy} \n")

                self.write_to_file(button, job_id, self.browser.title, result)

                # sleep every 20 applications
                if count_application != 0 and count_application % 20 == 0:
                    sleepTime: int = random.randint(500, 900)
                    log.info(f"""********count_application: {count_application}************\n\n
                                Time for a nap - see you in:{int(sleepTime / 60)} min
                            ****************************************\n\n""")
                    time.sleep(sleepTime)

        except Exception as e:
            log.error(e)
            raise e
    
    def write_to_file(self, button, job_id, browserTitle, result) -> None:
        def re_extract(text, pattern):
            target = re.search(pattern, text)
            if target:
                target = target.group(1)
            return target

        timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        attempted: bool = False if button == False else True
        job = re_extract(browserTitle.split(' | ')[0], r"\(?\d?\)?\s?(\w.*)")
        company = re_extract(browserTitle.split(' | ')[1], r"(\w.*)")

        toWrite: list = [timestamp, job_id, job, company, attempted, result]
        with open(self.filename, 'a') as f:
            writer = csv.writer(f)
            writer.writerow(toWrite)

    def get_job_page(self, job_id):

        job = 'https://www.linkedin.com/jobs/view/' + str(job_id)
        self.browser.get(job)
        self.job_page = self.load_page(sleep=0.5)
        return self.job_page

    def get_easy_apply_button(self):
        try:
            button = self.browser.find_elements("xpath",'//button[contains(@class, "jobs-apply-button")]')
            EasyApplyButton = button[1]
        except Exception as e: 
            print("Exception:",e)
            EasyApplyButton = False
        return EasyApplyButton


    def send_resume(self) -> bool:
        def is_present(button_locator) -> bool:
            return len(self.browser.find_elements(button_locator[0],button_locator[1])) > 0

        try:
            time.sleep(random.uniform(1.5, 2.5))
            next_locater = (By.CSS_SELECTOR,"button[aria-label='Continue to next step']")
            review_locater = (By.CSS_SELECTOR,"button[aria-label='Review your application']")
            submit_locater = (By.CSS_SELECTOR,"button[aria-label='Submit application']")
            submit_application_locator = (By.CSS_SELECTOR,"button[aria-label='Submit application']")
            error_locator = (By.CSS_SELECTOR,"p[data-test-form-element-error-message='true']")
            upload_locator = (By.CSS_SELECTOR, "input[name='file']")
            follow_locator = (By.CSS_SELECTOR, "label[for='follow-company-checkbox']")

            choose_resume = (By.CSS_SELECTOR,"button[aria-label='Choose Resume']")
            term_agree = (By.CSS_SELECTOR, "label[data-test-text-selectable-option__label='I Agree Terms & Conditions']")
            # TODO: put auto fill
            #class="fb-dash-form-element__error-field artdeco-text-input--input"

            submitted = False
            max_c_time = 60 * 1
            c_time = time.time()
            while time.time() - c_time < max_c_time:
                if is_present(choose_resume):
                        button: None = browser.wait.until(EC.element_to_be_clickable(choose_resume))
                        button.click()
                        time.sleep(random.uniform(1.5, 2.5))

                if is_present(term_agree):
                        button: None = browser.wait.until(EC.element_to_be_clickable(term_agree))
                        button.click()
                        time.sleep(random.uniform(1.5, 2.5))


                # Click Next or submitt button if possible
                button: None = None
                buttons: list = [next_locater, review_locater, follow_locator,submit_locater, submit_application_locator]
                for i, button_locator in enumerate(buttons):
                    if is_present(button_locator):
                        button: None = browser.wait.until(EC.element_to_be_clickable(button_locator))

                    if is_present(error_locator):
                        for element in self.browser.find_elements(error_locator[0],error_locator[1]):
                            text = element.text
                            if "Please enter a valid answer" in text:
                                button = None
                                break
                    if button:
                        button.click()
                        time.sleep(random.uniform(1.5, 2.5))
                        if i in (3, 4):
                            submitted = True
                        if i != 2:
                            break
                if button == None:
                    log.info("Could not complete submission")
                    break
                elif submitted:
                    log.info("Application Submitted")
                    break

            time.sleep(random.uniform(1.5, 2.5))


        except Exception as e:
            log.info(e)
            log.info("cannot apply to this job")
            raise (e)

        return submitted

    def load_page(self, sleep=1):
        scroll_page = 0
        while scroll_page < 4000:
            self.browser.execute_script("window.scrollTo(0," + str(scroll_page) + " );")
            scroll_page += 200
            time.sleep(sleep)

        if sleep != 1:
            self.browser.execute_script("window.scrollTo(0,0);")
            time.sleep(sleep * 3)

        page = BeautifulSoup(self.browser.page_source, "lxml")
        return page


    def next_jobs_page(self, position, location, jobs_per_page):
        base_url = "https://www.linkedin.com/jobs/search/?f_LF=f_AL&keywords="
        base_url = "https://www.linkedin.com/jobs/search/?f_AL=true&f_WT=2&keywords="

        self.browser.get(base_url + position + location + "&start=" + str(jobs_per_page))

        self.load_page()
        return (self.browser, jobs_per_page)

    def finish_apply(self) -> None:
        self.browser.close()


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
    )

    bot.start_apply()

if __name__ == '__main__':
    main()