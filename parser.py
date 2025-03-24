import asyncio
import os
import platform
import re

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
        # Check if the platform is Linux (for Ubuntu or similar systems)
        if platform.system() == "Linux":
            # Check if Chrome exists at the expected path
            chrome_path = "/usr/bin/google-chrome-stable"
            if not os.path.exists(chrome_path):
                chrome_path = "/usr/bin/google-chrome"  # Default location
                if not os.path.exists(chrome_path):
                    raise Exception("Chrome not found at the expected locations.")
        else:
            chrome_path = None  # On other systems, rely on the default binary location

        # Initialize the Driver with the correct Chrome binary location
        self.driver: Driver = Driver(
            uc=True,
            headless=True,
            binary_location=chrome_path  # Pass the Chrome path if found
        )
        self.previous_homes: list[Home] = []
        self.latest_homes: list[Home] = []
        self.settings = settings

    async def fetch_page(self, first_time=False):
        """
        Fetches the Funda page and handles popups/captchas during the first fetch.
        """
        try:
            logger.debug(f"Fetching data from {self.settings.funda_url}. Timeout: {WEBDRIVER_WAIT_TIMEOUT} sec")
            if first_time:
                logger.debug(f"First time: {first_time}")
            self.driver.get(self.settings.funda_url)

            # Wait for page elements to load - updated selector to match new HTML structure
            WebDriverWait(self.driver, WEBDRIVER_WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.flex.flex-col.sm\\:flex-row'))
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

            # Updated selector for closing popup
            try:
                close_button = WebDriverWait(self.driver, WEBDRIVER_WAIT_TIMEOUT).until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            "button[class*='absolute right-4 top-3 flex h-11 w-11 items-center justify-center']"
                        )
                    )
                )
                close_button.click()
                logger.info("Closed additional popup.")
            except TimeoutException:
                logger.warning("No popup found or unable to close it.")
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

        # Get all home container elements, skipping advertisements
        container_divs = soup.find_all("div", {"class": "border-b pb-3"})

        homes = []
        for container in container_divs:
            # Skip advertisements by checking for ad-related classes or IDs
            ad_element = container.find(["div"], {"id": re.compile(r'div-gpt-ad')})
            if ad_element:
                logger.debug("Skipping advertisement element")
                continue

            # Look for the main flex container that holds the home data
            flex_container = container.find("div", {"class": "flex flex-col sm:flex-row"})
            if not flex_container:
                continue

            home = self.extract_home_data(flex_container)
            if home.url:  # Only add if we have a valid URL
                home.map_url = f"{home.url}/#kaart"
                homes.append(home)

        return homes

    def extract_home_data(self, element):
        """
        Extracts home details from a single element.
        """
        # Find the home info container
        info_container = element.find("div",
                                      {"class": "relative flex w-full min-w-0 flex-col pl-0 pt-4 sm:pl-4 sm:pt-0"})
        if not info_container:
            return Home()

        # Extract URL and address info
        address_link = info_container.find("a", {"data-testid": "listingDetailsAddress"})
        url = address_link['href'] if address_link else None
        if url and not url.startswith('http'):
            url = f"https://www.funda.nl{url}"

        street_house_elem = address_link.find("span", {"class": "truncate"}) if address_link else None
        street_house = street_house_elem.text.strip() if street_house_elem else None

        postal_code_city_elem = address_link.find("div",
                                                  {"class": "truncate text-neutral-80"}) if address_link else None
        postal_code_city = postal_code_city_elem.text.strip() if postal_code_city_elem else None

        # Extract price
        price_elem = info_container.find("div", {"class": "truncate"}, text=re.compile(r'€'))
        price = price_elem.text.strip() if price_elem else None

        # Extract property info from list items
        size = None
        bedrooms = None
        energy_rating = None

        list_items = info_container.find_all("li", {"class": "flex items-center"})
        for item in list_items:
            item_text = item.text.strip()
            svg = item.find("svg")
            if svg:
                svg_path = svg.find("path")
                if svg_path:
                    path_d = svg_path.get("d", "")
                    # Identify what info this item represents by SVG path
                    if "m²" in item_text:
                        size = item_text
                    elif path_d.startswith("M11 20") or "bed" in item_text.lower():  # Path for bedrooms
                        bedrooms = item_text.strip()
                    elif path_d.startswith("M23.675") or any(
                            rating in item_text for rating in "ABCDEFG+"):  # Path for energy rating
                        energy_rating = item_text

        # Extract realtor info
        makelaar_elem = info_container.find("a", {"class": re.compile(r"truncate.*text-secondary-70")})
        makelaar_url = makelaar_elem['href'] if makelaar_elem else None
        makelaar_text = makelaar_elem.text.strip() if makelaar_elem else None

        return Home(
            url=url,
            street_house=street_house,
            postal_code_city=postal_code_city,
            price=price,
            size=size,
            bedrooms=bedrooms,
            energy_rating=energy_rating,
            makelaar_url=makelaar_url,
            makelaar_text=makelaar_text
        )

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
            if self.previous_homes:
                last_home = self.previous_homes[0]
                await message_queue.put(last_home.beautified_info)
            else:
                logger.warning("No homes found in initial fetch")

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