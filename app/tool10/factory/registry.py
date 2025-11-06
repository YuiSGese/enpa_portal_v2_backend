# tool_35_coupon_image_creation/factory/registry.py
from typing import Type, Dict
from .base_factory import Factory


class FactoryRegistry:
    """Đăng ký và quản lý các Factory Template."""

    def __init__(self):
        self._factories: Dict[str, Type[Factory]] = {}

    def register_factory(self, key: str, factory: Type[Factory]) -> None:
        """Đăng ký template factory."""
        self._factories[key] = factory

    def get_factory(self, key: str) -> Type[Factory]:
        """Lấy factory theo key."""
        factory = self._factories.get(str(key))
        if not factory:
            raise ValueError(f"テンプレートが存在しません: {key}")
        return factory


# Singleton registry
factory_registry = FactoryRegistry()
