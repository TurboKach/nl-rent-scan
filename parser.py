import asyncio
import json

from bs4 import BeautifulSoup
from seleniumbase import Driver
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from asyncio import Queue
from loguru import logger

message_queue = Queue()

async def fetch_data(url, driver, first_time=False):
    driver.get(url)
    # Increase the timeout if necessary
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-test-id="search-result-item"]'))
        )

        if first_time:
            logger.info("Successfully fetched data for the first time.")
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
            )
            # Click the button
            cookie_button.click()
            new_close_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "button[class='absolute right-4 top-3 flex h-11 w-11 items-center justify-center']"
                    )
                )
            )
            new_close_button.click()
    except TimeoutException:
        logger.warning("Timed out waiting for page to load")
        return None  # or handle it in some other way
    return driver.page_source


async def parse_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    elements = soup.find_all("div", {"data-test-id": "search-result-item"})
    return elements


async def extract_info(elements):
    # Extract and return the relevant information from the elements
    info = []
    for element in elements:
        # Initialize default values
        url = street_house = postal_code_city = price = size = bedrooms = energy_rating = makelaar_url = makelaar_text = None

        # Extract the URL
        link_element = element.find("a", {"data-test-id": "object-image-link"})
        if link_element:
            url = link_element["href"]

        # Extract the street_house
        street_house_element = element.find("h2", {"data-test-id": "street-name-house-number"})
        if street_house_element:
            street_house = street_house_element.get_text(strip=True)

        # Extract the postal code and city
        postal_code_city_element = element.find("div", {"data-test-id": "postal-code-city"})
        if postal_code_city_element:
            postal_code_city = postal_code_city_element.get_text(strip=True)

        # Extract the price
        price_element = element.find("p", {"data-test-id": "price-rent"})
        if price_element:
            price = price_element.get_text(strip=True)

        # Extract details from 'ul' list if present
        ul_element = element.find("ul", {"class": "mt-1 flex h-6 min-w-0 flex-wrap overflow-hidden"})
        if ul_element:
            li_elements = ul_element.find_all("li")
            for li_el in li_elements:
                if li_el.get_text(strip=True).endswith("m²"):
                    size = li_el.get_text(strip=True)
                elif li_el.get_text(strip=True)[0] in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                    bedrooms = li_el.get_text(strip=True)
                elif li_el.get_text(strip=True)[0] in ["A", "B", "C", "D", "E", "F", "G"]:
                    energy_rating = li_el.get_text(strip=True)

        # Extract the makelaar
        makelaar_element = (
            element.find("div", {"class": "mt-4 flex"})
            .find("a", {"class": "text-blue-2 min-w-0 cursor-pointer truncate"})
        )
        if makelaar_element:
            makelaar_url = makelaar_element["href"]
            makelaar_text = makelaar_element.get_text(strip=True)
        # Append extracted data, even if some is missing
        info.append(
            {
                "url": url,
                "map_url": f"{url}/#kaart",
                "street_house": street_house,
                "postal_code_city": postal_code_city,
                "price": price,
                "size": size,
                "bedrooms": bedrooms,
                "energy_rating": energy_rating,
                "makelaar_url": makelaar_url,
                "makelaar_text": makelaar_text,
            }
        )

    return info


async def check_new_elements(old_elements, new_elements):
    old_links = [element.get("href") for element in old_elements]
    return [element for element in new_elements if element.get("href") not in old_links]


async def update_seen_elements(seen_elements, new_elements_found, max_size=50):
    # Add the new elements to the seen_elements
    seen_elements.extend(new_elements_found)

    # If the list is longer than max_size, keep only the most recent max_size elements
    if len(seen_elements) > max_size:
        # Keep the last max_size elements
        seen_elements[:] = seen_elements[-max_size:]

    return seen_elements


async def scan_funda(url):
    # Set up Selenium WebDriver
    driver = Driver(uc=True, headless=True)

    try:
        html_content = await fetch_data(url, driver, first_time=True)
        elements = await parse_html(html_content)
        extracted_info = await extract_info(elements)
        logger.debug(f"Initial data: \n{extracted_info}")
        for info in extracted_info:
            message = (
                f"📍 {info['street_house']} {info['url']}\n"
                f"   {info['postal_code_city']}\n"
                f"💰 {info['price']}\n"
                f"🏠 {info['size']}\n"
                f"🛏️ {info['bedrooms']}\n"
                f"⚡️ {info['energy_rating']}"
                f"👤 {info['makelaar_text']} {info['makelaar_url']}\n"
            )
            await message_queue.put(message)
        seen_elements = extracted_info

        while True:
            with open("settings.json", "r") as f:
                settings = json.load(f)
                url = settings["funda_url"]
            logger.debug("Checking for new elements...")
            html_content = await fetch_data(url, driver)
            if html_content is None:
                logger.warning("Failed to fetch new data, trying again...")
                continue
            new_elements = await parse_html(html_content)
            new_info = await extract_info(new_elements)
            new_elements_found = await check_new_elements(seen_elements, new_info)

            if new_elements_found:
                logger.info("New elements found")
                for info in new_elements_found:
                    message = (
                        f"📍 {info['street_house']} {info['url']}\n"
                        f"   {info['postal_code_city']}\n"
                        f"💰 {info['price']}\n"
                        f"🏠 {info['size']}\n"
                        f"🛏️ {info['bedrooms']}\n"
                        f"⚡️ {info['energy_rating']}"
                        f"👤 {info['makelaar_text']} {info['makelaar_url']}\n"
                    )
                    await message_queue.put(message)
                seen_elements = await update_seen_elements(seen_elements, new_elements_found)
            else:
                logger.debug("No new elements found.")

            await asyncio.sleep(10)

    except KeyboardInterrupt:
        logger.info("Stopping the script.")
    finally:
        driver.quit()
