# tool_35_coupon_image_creation/factory/templates_factory.py
import os
from PIL import Image, ImageDraw
from datetime import datetime
from ..schemas import CouponInput
from .base_factory import Factory
from .registry import factory_registry


# ==========================
# FactoryTypeA〜D : Normal Banner
# ==========================

class FactoryTypeA(Factory):
    """Normal Banner type A"""
    def draw_from_json(self, data: CouponInput, save_path: str):
        img = Image.open(os.path.join("templates", f"coupon_{data.template}.jpg"))
        draw = ImageDraw.Draw(img)

        # Message 1 (upper text)
        self.place_text(draw, data.message1, self.font_path_NotoSans_EB, 500, 130, 60, color=(220,196,120))
        # Message 2 (main text)
        if data.message2:
            self.place_text(draw, data.message2, self.font_path_NotoSans_EB, 500, 230, 55, color=(255,255,255))
        # Discount
        discount_text = f"{data.discount_value}{data.discount_unit}"
        self.place_text(draw, discount_text, self.font_path_Lato, 500, 400, 180, color=(0,0,0))
        # Period
        if data.start_date and data.end_date:
            start = data.start_date.strftime("%m/%d %H:%M")
            end = data.end_date.strftime("%m/%d %H:%M")
            self.place_text(draw, f"{start} ~ {end}", self.font_path_Lato, 500, 750, 40, color=(255,255,255))
        img.save(save_path, quality=95)


class FactoryTypeB(Factory):
    """Normal Banner type B"""
    def draw_from_json(self, data: CouponInput, save_path: str):
        img = Image.open(os.path.join("templates", f"coupon_{data.template}.jpg"))
        draw = ImageDraw.Draw(img)

        self.place_text(draw, data.message1, self.font_path_NotoSans_M, 500, 130, 60, color=(200,200,200))
        discount_text = f"{data.discount_value}{data.discount_unit} OFF"
        self.place_text(draw, discount_text, self.font_path_Lato, 500, 400, 200, color=(210,165,90))
        if data.available_condition:
            self.place_text(draw, data.available_condition, self.font_path_NotoSans_M, 500, 700, 40, color=(255,255,255))
        img.save(save_path, quality=95)


class FactoryTypeC(Factory):
    """Normal Banner type C"""
    def draw_from_json(self, data: CouponInput, save_path: str):
        img = Image.open(os.path.join("templates", f"coupon_{data.template}.jpg"))
        draw = ImageDraw.Draw(img)

        self.place_text(draw, data.message1, self.font_path_NotoSans_EB, 500, 150, 60, color=(255,255,255))
        discount_text = f"{data.discount_value}{data.discount_unit} OFF"
        self.place_text(draw, discount_text, self.font_path_Lato, 500, 380, 200, color=(255,240,90))
        if data.start_date and data.end_date:
            start = data.start_date.strftime("%m/%d %H:%M")
            end = data.end_date.strftime("%m/%d %H:%M")
            self.place_text(draw, f"{start} ~ {end}", self.font_path_Lato, 500, 760, 40, color=(255,255,255))
        img.save(save_path, quality=95)


class FactoryTypeD(Factory):
    """Large Banner type D"""
    def draw_from_json(self, data: CouponInput, save_path: str):
        img = Image.open(os.path.join("templates", f"coupon_{data.template}.jpg"))
        draw = ImageDraw.Draw(img)
        self.place_text(draw, data.message1, self.font_path_NotoSans_EB, 700, 220, 80, color=(255,255,255))
        discount_text = f"{data.discount_value}{data.discount_unit}"
        self.place_text(draw, discount_text, self.font_path_Lato, 700, 450, 250, color=(255,255,255))
        img.save(save_path, quality=95)


# ==========================
# FactoryTypeA2〜D2 : Small / Vertical Banner
# ==========================

class FactoryTypeA2(Factory):
    """Small Banner type A2"""
    def draw_from_json(self, data: CouponInput, save_path: str):
        img = Image.open(os.path.join("templates", f"coupon_{data.template}.jpg"))
        draw = ImageDraw.Draw(img)
        self.place_text(draw, data.message1, self.font_path_NotoSans_EB, 540, 50, 50, color=(220,196,120))
        discount_text = f"{data.discount_value}{data.discount_unit}"
        self.place_text(draw, discount_text, self.font_path_Lato, 540, 130, 80, color=(0,0,0))
        img.save(save_path, quality=95)


class FactoryTypeB2(Factory):
    """Small Banner type B2"""
    def draw_from_json(self, data: CouponInput, save_path: str):
        img = Image.open(os.path.join("templates", f"coupon_{data.template}.jpg"))
        draw = ImageDraw.Draw(img)
        self.place_text(draw, data.message1, self.font_path_NotoSans_M, 540, 60, 50, color=(100,100,100))
        discount_text = f"{data.discount_value}{data.discount_unit} OFF"
        self.place_text(draw, discount_text, self.font_path_Lato, 540, 140, 80, color=(210,165,90))
        img.save(save_path, quality=95)


class FactoryTypeC2(Factory):
    """Vertical Banner type C2"""
    def draw_from_json(self, data: CouponInput, save_path: str):
        img = Image.open(os.path.join("templates", f"coupon_{data.template}.jpg"))
        draw = ImageDraw.Draw(img)
        # vertical text layout
        x, y = 200, 100
        for ch in f"{data.discount_value}{data.discount_unit}":
            self.place_text(draw, ch, self.font_path_Lato, x, y, 120, color=(255,255,255))
            y += 120
        self.place_text(draw, data.message1, self.font_path_NotoSans_M, 600, 800, 50, color=(255,255,255))
        img.save(save_path, quality=95)


class FactoryTypeD2(Factory):
    """Large Banner type D2"""
    def draw_from_json(self, data: CouponInput, save_path: str):
        img = Image.open(os.path.join("templates", f"coupon_{data.template}.jpg"))
        draw = ImageDraw.Draw(img)
        self.place_text(draw, data.message1, self.font_path_NotoSans_EB, 680, 180, 70, color=(255,255,255))
        discount_text = f"{data.discount_value}{data.discount_unit}"
        self.place_text(draw, discount_text, self.font_path_Lato, 680, 400, 250, color=(255,255,255))
        if data.available_condition:
            self.place_text(draw, data.available_condition, self.font_path_NotoSans_M, 680, 620, 40, color=(255,255,255))
        img.save(save_path, quality=95)


# ==========================
# Đăng ký 18 Factory
# ==========================

factory_registry.register_factory("1", FactoryTypeA)
factory_registry.register_factory("2", FactoryTypeB)
factory_registry.register_factory("3", FactoryTypeC)
factory_registry.register_factory("4", FactoryTypeA)
factory_registry.register_factory("5", FactoryTypeB)
factory_registry.register_factory("6", FactoryTypeC)
factory_registry.register_factory("7", FactoryTypeA2)
factory_registry.register_factory("8", FactoryTypeB2)
factory_registry.register_factory("9", FactoryTypeA2)
factory_registry.register_factory("10", FactoryTypeB2)
factory_registry.register_factory("11", FactoryTypeC2)
factory_registry.register_factory("12", FactoryTypeC2)
factory_registry.register_factory("13", FactoryTypeC2)
factory_registry.register_factory("14", FactoryTypeD)
factory_registry.register_factory("15", FactoryTypeD)
factory_registry.register_factory("16", FactoryTypeD)
factory_registry.register_factory("17", FactoryTypeD2)
factory_registry.register_factory("18", FactoryTypeD2)
