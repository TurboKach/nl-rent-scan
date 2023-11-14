import asyncio

from bs4 import BeautifulSoup
from seleniumbase import Driver
from selenium.common import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger

from settings import message_queue, settings


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

    def __str__(self):
        return self.__dict__.__repr__()

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
            # f'👤 <a href="{self.makelaar_url}">{self.makelaar_text}</a>\n'
        )


class FundaParser:
    def __init__(self):
        self.driver: Driver = Driver(uc=True, headless=True)
        self.previous_homes: list[Home] = []
        self.latest_homes: list[Home] = []
        self.settings = settings

    async def fetch_data(self, first_time=False):
        data_fetched = False
        while not data_fetched:
            try:
                logger.debug(f"Fetching data from {self.settings.funda_url}")
                self.driver.get(self.settings.funda_url)

                # Increase the timeout if necessary
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-test-id="search-result-item"]'))
                )

                if first_time:
                    logger.info("Successfully fetched data for the first time.")
                    cookie_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
                    )
                    # Click the button
                    cookie_button.click()
                    logger.info("Clicked the cookie button.")
                    new_close_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            (
                                By.CSS_SELECTOR,
                                "button[class='absolute right-4 top-3 flex h-11 w-11 items-center justify-center']"
                            )
                        )
                    )
                    new_close_button.click()
                    logger.info("Clicked the new close button.")
                data_fetched = True
            except TimeoutException:
                logger.warning("Timed out waiting for page to load")
                return None  # or handle it in some other way
            except WebDriverException:
                logger.error("Webdriver exception")
                if self.driver.current_url != self.settings.funda_url:
                    self.settings.funda_url = self.settings.funda_url_default
                return None
                # self.driver: Driver = Driver(uc=True, headless=True)
            # if self.driver.current_url != self.settings.funda_url:
            #     self.settings.funda_url = self.settings.funda_url_default
            #     logger.warning("Failed to fetch data, setting default url and trying again...")
            #     return None

    async def extract_home_info(self):
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        elements = soup.find_all("div", {"data-test-id": "search-result-item"})

        # Extract and return the relevant information from the elements
        homes = []
        for element in elements:
            # Initialize default values
            home = Home()

            # Extract the URL
            link_element = element.find("a", {"data-test-id": "object-image-link"})
            if link_element:
                home.url = link_element["href"]

            # Extract the street_house
            street_house_element = element.find("h2", {"data-test-id": "street-name-house-number"})
            if street_house_element:
                home.street_house = street_house_element.get_text(strip=True)

            # Extract the postal code and city
            postal_code_city_element = element.find("div", {"data-test-id": "postal-code-city"})
            if postal_code_city_element:
                home.postal_code_city = postal_code_city_element.get_text(strip=True)

            # Extract the price
            price_element = element.find("p", {"data-test-id": "price-rent"})
            if price_element:
                home.price = price_element.get_text(strip=True)

            # Extract details from 'ul' list if present
            ul_element = element.find("ul", {"class": "mt-1 flex h-6 min-w-0 flex-wrap overflow-hidden"})
            if ul_element:
                li_elements = ul_element.find_all("li")
                for li_el in li_elements:
                    if li_el.get_text(strip=True).endswith("m²"):
                        home.size = li_el.get_text(strip=True)
                    elif li_el.get_text(strip=True)[0] in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                        home.bedrooms = li_el.get_text(strip=True)
                    elif li_el.get_text(strip=True)[0] in ["A", "B", "C", "D", "E", "F", "G"]:
                        home.energy_rating = li_el.get_text(strip=True)

            # Extract the makelaar
            makelaar_element = (
                element.find("div", {"class": "mt-4 flex"})
                .find("a", {"class": "text-blue-2 min-w-0 cursor-pointer truncate"})
            )
            if makelaar_element:
                home.makelaar_url = makelaar_element["href"]
                home.makelaar_text = makelaar_element.get_text(strip=True)
            # Append extracted data, even if some is missing
            home.map_url = f"{home.url}/#kaart"
            homes.append(home)

        return homes

    async def check_new_homes(self):
        old_homes_urls = [home.url for home in self.previous_homes]
        return [home for home in self.latest_homes if home.url not in old_homes_urls]

    async def scan_funda(self):

        try:
            # Fetch the data for the first time
            await self.fetch_data(first_time=True)
            self.previous_homes = await self.extract_home_info()
            logger.debug(f"Initial data: \n{self.previous_homes}")
            last_home = self.previous_homes[0]
            logger.debug(f"Adding last home {last_home.url} to queue...")
            await message_queue.put(last_home.beautified_info)

            while True:
                # Now fetch the newest data
                logger.debug("Checking for new homes...")
                await self.fetch_data(first_time=False)
                if self.driver.page_source is None:
                    logger.warning("Failed to fetch new data, trying again...")
                    continue
                extracted_homes = await self.extract_home_info()
                if extracted_homes is None:
                    logger.warning("Failed to extract new data, trying again...")
                    continue
                self.latest_homes = extracted_homes
                new_homes = await self.check_new_homes()

                if new_homes:
                    logger.info(f" {len(new_homes)} new homes found")
                    logger.debug(f"New data: \n{new_homes}")
                    for home in new_homes:
                        logger.debug(f"Adding new home {home.url} to queue...")
                        await message_queue.put(home.beautified_info)
                else:
                    logger.debug(f"No new homes found. {len(self.latest_homes)} homes found.")

                # Update the previous homes
                self.previous_homes = self.latest_homes

                await asyncio.sleep(10)

        except KeyboardInterrupt:
            logger.info("Stopping the script.")
        finally:
            self.driver.quit()


parser = FundaParser()
