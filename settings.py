import json
from asyncio import Queue

from loguru import logger


class Settings:
    def __init__(self):
        self.funda_url_default: str = (
            "https://www.funda.nl/en/zoeken/huur"
            "?selected_area=%5B%22amsterdam,50km%22%5D&sort=%22date_down%22"
        )
        self._funda_url: str = self.funda_url_default
        self._known_chats: list = []
        self.load()

    def load(self):
        with open("settings.json", "r") as f:
            _settings = json.load(f)
        self._funda_url = _settings.get("_funda_url") or self._funda_url
        self._known_chats = _settings.get("_known_chats") or self._known_chats
        logger.debug(f"Loaded settings: {self.__dict__}")

    def save(self):
        with open("settings.json", "w") as f:
            logger.debug(f"Saving settings: {self.__dict__}")
            json.dump(self.__dict__, f)

    @property
    def funda_url(self):
        return self._funda_url

    @funda_url.setter
    def funda_url(self, value):
        logger.info(f"New url set: {value}")
        self._funda_url: str = value
        self.save()

    @funda_url.deleter
    def funda_url(self):
        del self._funda_url

    @property
    def known_chats(self):
        return self._known_chats

    @known_chats.setter
    def known_chats(self, value):
        logger.info(f"New chat added: {value}")
        self._known_chats: list = value
        self.save()

    @known_chats.deleter
    def known_chats(self):
        del self._known_chats


settings = Settings()

message_queue = Queue()

