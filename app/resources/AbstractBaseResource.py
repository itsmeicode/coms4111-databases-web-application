from abc import ABC, abstractmethod
from pydantic import BaseModel

class AbstractBaseResource(ABC):

    def __init__(self, config:dict) -> None:
        self._config = config

    @abstractmethod
    def get(self, template: dict) -> BaseModel:
        pass

    @abstractmethod
    def get_by_id(self, id: str) -> BaseModel:
        pass

    @abstractmethod
    def post(self, new_data: BaseModel) -> str:
        pass

    @abstractmethod
    def delete(self, id: str) -> int:
        pass

    @abstractmethod
    def put(self, character_id: str, new_data: BaseModel) -> int:
        pass


