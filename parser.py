import asyncio

from bs4 import BeautifulSoup
from seleniumbase import Driver
from selenium.common import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger

from settings import message_queue, settings

WEBDRIVER_WAIT_TIMEOUT = 10


class Home:
    def __init__(self, **kwargs):
        self.url = kwargs.get('url')
        self.map_url = kwargs.get('map_url')
        self.street_house = kwargs.get('street_house')
        self.postal_code_city = kwargs.get('postal_code_city')
        self.price = kwargs.get('price')
        self.size = kwargs.get('size')
        self.bedrooms = kwargs.get('bedrooms')
        self.energy_rating = kwargs.get('energy_rating', 'N/A')
        self.makelaar_url = kwargs.get('makelaar_url')
        self.makelaar_text = kwargs.get('makelaar_text')

    def __repr__(self):
        return (
            f"<Home street_house={self.street_house}, "
            f"price={self.price}, "
            f"size={self.size}, "
            f"bedrooms={self.bedrooms}, "
            f"energy_rating={self.energy_rating}>"
        )

    @property
    def beautified_info(self):
        return (
            f"📍 <a href='{self.url}'>{self.street_house}</a>\n"
            f"     \t{self.postal_code_city}\n\n"
            f"💰 {self.price}\n"
            f"🏠 {self.size}\n"
            f"🛏️ {self.bedrooms}\n"
            f"⚡️ {self.energy_rating}\n"
            f'👤 {self.makelaar_text}\n'
        )


class FundaParser:
    def __init__(self):
        self.driver: Driver = Driver(uc=True, headless=True)
        self.previous_homes: list[Home] = []
        self.latest_homes: list[Home] = []
        self.settings = settings

    async def fetch_page(self, first_time=False):
        """
        Fetches the Funda page and handles popups/captchas during the first fetch.
        """
        try:
            logger.debug(f"Fetching data from {self.settings.funda_url}. Timeout: {WEBDRIVER_WAIT_TIMEOUT} sec")
            self.driver.get(self.settings.funda_url)

            # Wait for page elements to load
            WebDriverWait(self.driver, WEBDRIVER_WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-test-id="search-result-item"]'))
            )

            if first_time:
                self.handle_initial_popups()
            return True
        except TimeoutException:
            logger.warning("Timed out waiting for page to load")
        except WebDriverException:
            logger.error("WebDriverException encountered")
            self.handle_driver_exception()
        return False

    def handle_initial_popups(self):
        """
        Handles cookies, captchas, or other initial popups on the first page load.
        """
        try:
            logger.info("Handling cookie consent and popups...")
            cookie_button = WebDriverWait(self.driver, WEBDRIVER_WAIT_TIMEOUT).until(
                EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
            )
            cookie_button.click()
            logger.info("Cookie consent accepted.")

            close_button = WebDriverWait(self.driver, WEBDRIVER_WAIT_TIMEOUT).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "button[class='absolute right-4 top-3 flex h-11 w-11 items-center justify-center']"
                    )
                )
            )
            close_button.click()
            logger.info("Closed additional popup.")
        except TimeoutException:
            logger.warning("Timed out handling initial popups.")

    def handle_driver_exception(self):
        """
        Handles exceptions by resetting the URL to default if the page cannot load.
        """
        if self.driver.current_url != self.settings.funda_url:
            self.settings.funda_url = self.settings.funda_url_default
            logger.info("Reset URL to default.")

    async def extract_home_info(self):
        """
        Extracts home information from the loaded page.
        """
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        elements = soup.find_all("div", {"data-test-id": "search-result-item"})

        homes = []
        for element in elements:
            home = self.extract_home_data(element)
            home.map_url = f"{home.url}/#kaart"
            homes.append(home)
        return homes

    def extract_home_data(self, element):
        """
        Extracts home details from a single element.
        """
        home = Home(
            url=self.extract_element_attr(element, "a[data-test-id='object-image-link']", "href"),
            street_house=self.extract_element_text(element, "h2[data-test-id='street-name-house-number']"),
            postal_code_city=self.extract_element_text(element, "div[data-test-id='postal-code-city']"),
            price=self.extract_element_text(element, "p[data-test-id='price-rent']"),
            makelaar_url=self.extract_element_attr(element, "div.mt-4.flex a.text-blue-2", "href"),
            makelaar_text=self.extract_element_text(element, "div.mt-4.flex a.text-blue-2")
        )

        self.extract_home_additional_info(home, element)
        return home

    def extract_home_additional_info(self, home, element):
        """
        Extracts additional information such as size, bedrooms, and energy rating.
        """
        ul_element = element.find("ul", {"class": "mt-1 flex h-6 min-w-0 flex-wrap overflow-hidden"})
        if ul_element:
            li_elements = ul_element.find_all("li")
            for li in li_elements:
                text = li.get_text(strip=True)
                if text.endswith("m²"):
                    home.size = text
                elif text.isdigit():
                    home.bedrooms = text
                elif text[0] in "ABCDEFG":
                    home.energy_rating = text

    @staticmethod
    def extract_element_text(element, selector):
        """
        Extracts text content from a BeautifulSoup element.
        """
        tag = element.select_one(selector)
        return tag.get_text(strip=True) if tag else None

    @staticmethod
    def extract_element_attr(element, selector, attr):
        """
        Extracts an attribute from a BeautifulSoup element.
        """
        tag = element.select_one(selector)
        return tag[attr] if tag else None

    async def check_new_homes(self):
        """
        Compares the latest homes with previously fetched homes and returns new ones.
        """
        old_homes_urls = [home.url for home in self.previous_homes]
        return [home for home in self.latest_homes if home.url not in old_homes_urls]

    async def scan_funda(self):
        """
        Periodically scans Funda for new homes and updates the queue.
        """
        try:
            if not await self.fetch_page(first_time=True):
                return

            self.previous_homes = await self.extract_home_info()
            logger.debug(f"Initial data fetched: {self.previous_homes}")
            last_home = self.previous_homes[0]
            await message_queue.put(last_home.beautified_info)

            while True:
                logger.debug("Checking for new homes...")
                if not await self.fetch_page():
                    continue

                self.latest_homes = await self.extract_home_info()
                new_homes = await self.check_new_homes()

                if new_homes:
                    logger.info(f"{len(new_homes)} new homes found.")
                    for home in new_homes:
                        await message_queue.put(home.beautified_info)
                else:
                    logger.debug("No new homes found.")

                self.previous_homes = self.latest_homes
                await asyncio.sleep(10)
        except KeyboardInterrupt:
            logger.info("Stopping the script.")
        finally:
            self.driver.quit()


# Initialize the parser instance
parser = FundaParser()
