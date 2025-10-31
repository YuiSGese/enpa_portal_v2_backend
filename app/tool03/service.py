# -*- coding: utf-8 -*-
import os
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
import asyncio
from decimal import Decimal, ROUND_HALF_UP
import time
import tempfile
import ftplib
import logging
import datetime  # <<< datetime のインポートを追加

# 同じディレクトリ (.) から schemas をインポート
from .schemas import Tool03ProductRowInput, Tool03JobStatusResponse, Tool03ImageResult

# --- パス解決ロジック ---
# ... (パスロジック部分は変更なし) ...
SERVICE_FILE_PATH = Path(__file__).resolve()
APP_DIR = SERVICE_FILE_PATH.parent.parent
PROJECT_ROOT = APP_DIR.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
if not ASSETS_DIR.is_dir():
    ASSETS_DIR = APP_DIR / "assets"
    if not ASSETS_DIR.is_dir():
        raise FileNotFoundError(
            f"assets ディレクトリが見つかりません: {PROJECT_ROOT / 'assets'} または {APP_DIR / 'assets'}"
        )
FONTS_DIR = ASSETS_DIR / "fonts"
if not FONTS_DIR.is_dir():
     raise FileNotFoundError(f"フォントディレクトリが見つかりません: {FONTS_DIR}")
TOOL03_TEMPLATES_DIR_OPTION1 = ASSETS_DIR / "tool03" / "templates"
TOOL03_TEMPLATES_DIR_OPTION2 = APP_DIR / "tool03" / "assets" / "templates"
if TOOL03_TEMPLATES_DIR_OPTION1.is_dir():
    TOOL03_TEMPLATES_DIR = TOOL03_TEMPLATES_DIR_OPTION1
elif TOOL03_TEMPLATES_DIR_OPTION2.is_dir():
    TOOL03_TEMPLATES_DIR = TOOL03_TEMPLATES_DIR_OPTION2
else:
    raise FileNotFoundError(
        f"Tool 03 テンプレートディレクトリが見つかりません: {TOOL03_TEMPLATES_DIR_OPTION1} または {TOOL03_TEMPLATES_DIR_OPTION2}"
    )
# --- パス解決ロジックの終わり ---


# ジョブストレージパス
JOB_STORAGE_BASE_DIR = PROJECT_ROOT / "storage" / "tool03_jobs"
JOB_STORAGE_BASE_DIR.mkdir(parents=True, exist_ok=True)

# --- ジョブステータスストレージ (インメモリ) ---
job_tracker: Dict[str, Dict[str, Any]] = {}
# ----------------------------------------------


# === ヘルパー関数 ===
def calculate_font_size(text: str, font_path: str, box_width: int, box_height: int) -> int:
    font_size = 1
    max_font_size = box_height + 10
    try:
        while font_size <= max_font_size:
            font = ImageFont.truetype(str(font_path), font_size)
            bbox = font.getbbox(text)
            if bbox is None: return max(1, font_size - 1)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if width > box_width or height > box_height:
                return max(1, font_size - 1)
            font_size += 1
        return max(1, font_size - 1)
    except IOError:
        logging.error(f"フォントファイルを開けません: {font_path}")
        return 1
    except Exception as e:
        logging.error(f"フォント '{font_path}' のサイズ計算中にエラー: {e}")
        return 1


# === Factory Pattern ===

class FactoryRegistry:
    def __init__(self):
        self._factories: Dict[str, type] = {}
    def register_factory(self, key: str, factory_cls: type):
        if not issubclass(factory_cls, BaseImageFactory):
            raise TypeError("factory_cls は BaseImageFactory を継承する必要があります")
        self._factories[key] = factory_cls
        logging.debug(f"Factory 登録済み: {key} -> {factory_cls.__name__}")
    def get_factory(self, key: str) -> 'BaseImageFactory':
        logging.debug(f"キー '{key}' の Factory を検索中")
        factory_cls = self._factories.get(key)
        if not factory_cls:
            base_key = key.split('-')[0]
            logging.debug(f"キー '{key}' が見つかりません。基本キー '{base_key}' を試行します")
            factory_cls = self._factories.get(base_key)
            if not factory_cls:
                logging.error(f"キー '{key}' と基本キー '{base_key}' の両方に Template Factory が存在しません")
                raise ValueError(f"Template Factory が存在しません: {key}")
        logging.debug(f"キー '{key}' に対して Factory クラス {factory_cls.__name__} を使用します")
        return factory_cls()

factory_registry = FactoryRegistry()

class BaseImageFactory:
    # --- フォントと色の定義 ---
    def __init__(self):
        self.font_path_arial=FONTS_DIR/'ARIALNB.TTF';self.font_path_yugothB=FONTS_DIR/'YuGothB.ttc';self.font_path_noto_sans_black=FONTS_DIR/'NotoSansJP-Black.ttf';self.font_path_noto_sans_bold=FONTS_DIR/'NotoSansJP-Bold.ttf';self.font_path_noto_sans_medium=FONTS_DIR/'NotoSansJP-Medium.ttf';self.font_path_noto_serif_extrabold=FONTS_DIR/'NotoSerifJP-ExtraBold.ttf';self.font_path_reddit=FONTS_DIR/'RedditSans-ExtraBold.ttf';self.font_path_reddit_condensed_extrabold=FONTS_DIR/'RedditSansCondensed-ExtraBold.ttf';self.font_path_shippori_bold=FONTS_DIR/'ShipporiMinchoB1-Bold.ttf';self.font_path_public_sans_bold=FONTS_DIR/'PublicSans-Bold.ttf'
        self.WHITE=(255,255,255);self.BLACK=(0,0,0);self.RED=(255,0,0)
        self.width=800;self.height=800
        self.mobile_start_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':35,'y1':1250,'x2':475,'y2':1319,'align':'right'};
        self.mobile_end_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':535,'y1':1250,'x2':975,'y2':1319,'align':'left'}

    # --- ヘルパー関数 ---
    def get_template_path(self, template_key: str, has_mobile_data: bool) -> Path:
        base_key = template_key.split('-')[0]
        template_file_name_base = f"template_{base_key}"
        suffix = ".jpg"
        mobile_template_path = TOOL03_TEMPLATES_DIR / f"{template_file_name_base}-2{suffix}"
        normal_template_path = TOOL03_TEMPLATES_DIR / f"{template_file_name_base}{suffix}"
        if has_mobile_data and mobile_template_path.exists():
            logging.debug(f"モバイルテンプレートを使用: {mobile_template_path}")
            return mobile_template_path
        if not normal_template_path.exists():
            logging.error(f"基本テンプレートが存在しません: {normal_template_path}")
            raise FileNotFoundError(f"基本テンプレートが存在しません: {normal_template_path}")
        logging.debug(f"通常テンプレートを使用: {normal_template_path}")
        return normal_template_path

    def _get_text_size(self, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        try:
            bbox = font.getbbox(text)
            if bbox is None: return 0, 0
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            return width, height
        except Exception as e:
            logging.error(f"'{text}' の _get_text_size でエラー: {e}")
            return 0, 0

    def _place_text(self, draw: ImageDraw, params: Dict[str, Any]):
        text = str(params.get('text', ''))
        if not text:
            return
        font_path = str(params['font_path'])
        font_color = params['font_color']
        x1, y1, x2, y2 = params['x1'], params['y1'], params['x2'], params['y2']
        align = params.get('align', 'left')
        box_width = x2 - x1
        box_height = y2 - y1
        if box_width <= 0 or box_height <= 0:
            logging.warning(f"テキスト '{text}' のバウンディングボックスが無効です: ({x1},{y1})-({x2},{y2})")
            return
        font_size = calculate_font_size(text, font_path, box_width, box_height)
        if font_size <= 0:
             logging.warning(f"テキスト '{text}' の計算済みフォントサイズが0以下です (ボックス: ({x1},{y1})-({x2},{y2}))")
             return
        try:
            font = ImageFont.truetype(font_path, font_size)
            text_width, _ = self._get_text_size(text, font)
            if align == 'left':
                x = x1
            elif align == 'center':
                x = x1 + (box_width - text_width) / 2
            elif align == 'right':
                x = x2 - text_width
            else:
                x = x1
            bbox = font.getbbox(text)
            if bbox is None: raise ValueError("フォントがテキスト配置用の None bbox を返しました")
            text_actual_height = bbox[3] - bbox[1]
            y_offset = bbox[1]
            y = y1 + (box_height - text_actual_height) / 2 - y_offset
            draw.text((x, y), text, fill=font_color, font=font)
        except Exception as e:
            logging.error(f"テキスト '{text}' (フォント {font_path} サイズ {font_size}) の描画中にエラー: {e}", exc_info=True)

    def _format_price(self, price_str: Optional[str]) -> str:
        if price_str is None: return ""
        try:
            price_decimal = Decimal(price_str).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            return f"{int(price_decimal):,}"
        except Exception:
            return str(price_str)

    def _calculate_discount_display(self, regular_price_str: Optional[str], sale_price_str: Optional[str], discount_type: Optional[str]) -> str:
        if regular_price_str is None or sale_price_str is None: return ""
        try:
            regular_price = Decimal(regular_price_str)
            sale_price = Decimal(sale_price_str)
            if regular_price <= 0 or regular_price <= sale_price: return ""
            difference = regular_price - sale_price
            if discount_type == "yen":
                discount_val = difference.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                return f"{int(discount_val):,}円"
            else:
                percentage = (difference / regular_price * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                return f"{int(percentage)}%"
        except Exception as e:
            logging.warning(f"割引計算エラー ({regular_price_str}, {sale_price_str}, {discount_type}): {e}")
            return ""

    def _format_datetime_jp(self, iso_str: Optional[str]) -> str:
        """ISO (YYYY-MM-DDTHH:mm) 形式の日付文字列を日本語形式 (MM月DD日HH:mm) に変換します。"""
        if not iso_str:
            return ""
        try:
            # fromisoformat を使って ISO 文字列をパース
            dt = datetime.datetime.fromisoformat(iso_str)
            # f-string を使って 0 埋めなしでフォーマット
            return f"{dt.month}月{dt.day}日{dt.hour}:{dt.minute:02d}"
        except ValueError:
            logging.warning(f"無効な日付形式のため、そのまま返します: {iso_str}")
            return iso_str # パース失敗時は元の文字列をそのまま返す
        except Exception as e:
            logging.error(f"日付フォーマットエラー ({iso_str}): {e}")
            return iso_str # その他のエラー時も元の文字列を返す
    # ----------------------------------------------

    def _place_price_group(self, draw: ImageDraw, price_params: Dict, unit_params: Dict, suffix_params: Dict):
        price_text = str(price_params.get('text', ''))
        unit_text = str(unit_params.get('text', ''))
        suffix_text = str(suffix_params.get('text', ''))
        if not price_text: return
        gap_width = 5
        try:
            price_font = ImageFont.truetype(str(price_params['font_path']), price_params['font_size'])
            unit_font = ImageFont.truetype(str(unit_params['font_path']), unit_params['font_size']) if unit_text else None
            suffix_font = ImageFont.truetype(str(suffix_params['font_path']), suffix_params['font_size']) if suffix_text else None
            price_w, _ = self._get_text_size(price_text, price_font)
            unit_w, _ = self._get_text_size(unit_text, unit_font) if unit_font else (0, 0)
            suffix_w, _ = self._get_text_size(suffix_text, suffix_font) if suffix_font else (0, 0)
            total_width = price_w
            if unit_text: total_width += gap_width + unit_w
            if suffix_text: total_width += gap_width + suffix_w
            container_width = price_params['x_end'] - price_params['x_origin']
            start_x = price_params['x_origin'] + (container_width - total_width) / 2
            price_y = price_params['y_origin']
            draw.text((start_x, price_y), price_text, fill=price_params['font_color'], font=price_font)
            current_x = start_x + price_w
            if unit_font:
                current_x += gap_width
                unit_y = price_y + unit_params.get('dy', 0)
                draw.text((current_x, unit_y), unit_text, fill=unit_params['font_color'], font=unit_font)
                current_x += unit_w
            if suffix_font:
                current_x += gap_width
                suffix_y = price_y + suffix_params.get('dy', 0)
                draw.text((current_x, suffix_y), suffix_text, fill=suffix_params['font_color'], font=suffix_font)
        except Exception as e:
            logging.error(f"価格 '{price_text}' の _place_price_group でエラー: {e}", exc_info=True)

    def draw(self, row_data: Tool03ProductRowInput, template_key: str) -> Image.Image:
        has_mobile_data = bool(row_data.mobileStartDate and row_data.mobileEndDate)
        original_height = self.height
        try:
            template_path = self.get_template_path(template_key, has_mobile_data)
            if has_mobile_data and template_path.name.endswith("-2.jpg") and hasattr(self, '_draw_mobile_details'):
                self.height = 1370
                logging.debug(f"モバイルテンプレート {template_path.name} のため、一時的に高さを 1370 に設定")
            img = Image.open(template_path).convert("RGB")
            draw_obj = ImageDraw.Draw(img)
            self._draw_details(draw_obj, row_data)
            if has_mobile_data and hasattr(self, '_draw_mobile_details') and callable(getattr(self, '_draw_mobile_details')):
                 if template_path.name.endswith("-2.jpg"):
                     logging.debug(f"{template_key} の _draw_mobile_details を呼び出し")
                     self._draw_mobile_details(draw_obj, row_data)
                 else:
                     logging.warning(f"モバイルデータはありますが、{template_key} のモバイルテンプレートが見つからないため、モバイル詳細はスキップします。")
            return img
        except FileNotFoundError:
            logging.error(f"テンプレートキー '{template_key}' (モバイル: {has_mobile_data}) のテンプレートファイルが見つかりません")
            raise
        except Exception as e:
            logging.error(f"テンプレートキー '{template_key}' の画像描画中に不明なエラー: {e}", exc_info=True)
            raise
        finally:
            self.height = original_height

    def _draw_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        raise NotImplementedError

    def _draw_mobile_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        logging.debug(f"{self.__class__.__name__} のデフォルト _draw_mobile_details を呼び出し")
        if row_data.mobileStartDate:
            self._place_text(draw, {**self.mobile_start_datetime_params, 'text': self._format_datetime_jp(row_data.mobileStartDate)})
        if row_data.mobileEndDate:
            self._place_text(draw, {**self.mobile_end_datetime_params, 'text': self._format_datetime_jp(row_data.mobileEndDate)})
        # -----------------------------------------

# --- Factory の実装 (A, B, B2, C, C2, ...) ---
class FactoryTypeA(BaseImageFactory):
    def __init__(self):
        super().__init__()
        self.width, self.height = 800, 880
        self.RED = (189, 41, 39)
        self.start_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.BLACK,'x1':270,'y1':80,'x2':771,'y2':125,'align':'center'}
        self.end_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.BLACK,'x1':270,'y1':190,'x2':771,'y2':235,'align':'center'}
        self.message_params={'font_path':self.font_path_noto_sans_black,'font_color':self.RED,'x1':30,'y1':280,'x2':770,'y2':370,'align':'center'}
        
        # --- 新規追加 (START) ---
        # RTF (800px) とサンプルに基づく。左揃えの代わりに中央揃え。
        self.price_type_params={'font_path':self.font_path_noto_sans_bold, 'font_color':self.WHITE, 'x1':65, 'y1':410, 'x2':805, 'y2':450, 'align':'left'}
        # --- 新規追加 (END) ---

        self.normal_price_group={
            # X座標は価格 (price)、単位 (unit)、接尾辞 (suffix) のみを含むように調整
            'price': {'text':'', 'font_path':self.font_path_public_sans_bold,'font_size':60,'font_color':self.WHITE,'x_origin':330,'x_end':740,'y_origin':395},
            'unit':  {'text':'円', 'font_path':self.font_path_noto_sans_black, 'font_size':30,'font_color':self.WHITE,'dy':20},
            'suffix':{'text':'のところ','font_path':self.font_path_noto_sans_black,'font_size':25,'font_color':self.WHITE,'dy':25}
        }
        self.discount_group={
             'price': {'text':'', 'font_path':self.font_path_public_sans_bold,'font_size':85,'font_color':self.BLACK,'x_origin':0,'x_end':self.width,'y_origin':485},
             'unit':  {'text':'', 'font_path':self.font_path_noto_sans_black, 'font_size':50,'font_color':self.BLACK,'dy':20},
             'suffix':{'text':'OFF','font_path':self.font_path_noto_sans_black,'font_size':30,'font_color':self.BLACK,'dy':45}
        }
        self.sale_price_group={
            'price': {'text':'', 'font_path':self.font_path_public_sans_bold,'font_size':160,'font_color':self.RED,'x_origin':0,'x_end':self.width,'y_origin':620},
            'unit':  {'text':'円', 'font_path':self.font_path_noto_sans_black, 'font_size':50,'font_color':self.RED,'dy':90},
            'suffix':{'text':'税込','font_path':self.font_path_noto_sans_black,'font_size':20,'font_color':self.RED,'dy':70}
        }
    def _draw_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        self._place_text(draw, {**self.start_datetime_params, 'text': self._format_datetime_jp(row_data.startDate)})
        self._place_text(draw, {**self.end_datetime_params, 'text': self._format_datetime_jp(row_data.endDate)})
        # -----------------------------------------
        self._place_text(draw, {**self.message_params, 'text': row_data.saleText or ""})
        
        # --- 新規追加 (START) ---
        # priceType を描画 (例: 当店通常価格)
        self._place_text(draw, {**self.price_type_params, 'text': row_data.priceType or ""})
        # --- 新規追加 (END) ---

        # 注意: 'normal_price_group' は priceType を含まず、価格のみを描画するようになりました
        # (サンプル 001 に基づくと、priceType と price は異なる位置にあるようで、古いコードロジックとは少し異なる可能性があります)
        # 要件に従い一時的に分離。
        self.normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        
        self.sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        self.discount_group['price']['text'] = discount_number
        self.discount_group['unit']['text'] = discount_unit_text
        self._place_price_group(draw, self.normal_price_group['price'], self.normal_price_group['unit'], self.normal_price_group['suffix'])
        self._place_price_group(draw, self.discount_group['price'], self.discount_group['unit'], self.discount_group['suffix'])
        self._place_price_group(draw, self.sale_price_group['price'], self.sale_price_group['unit'], self.sale_price_group['suffix'])
factory_registry.register_factory('A', FactoryTypeA)

class FactoryTypeB(BaseImageFactory):
    def __init__(self):
        super().__init__()
        self.width, self.height = 1000, 1000
        self.YELLOW=(255,239,0); self.RED=(215,0,0)
        self.start_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.RED,'x1':25,'y1':162,'x2':465,'y2':231,'align':'right'}
        self.end_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.RED,'x1':555,'y1':162,'x2':995,'y2':231,'align':'left'}
        self.message_params={'font_path':self.font_path_noto_sans_black,'font_color':self.RED,'x1':107,'y1':38,'x2':894,'y2':148,'align':'center'}
        
        # --- 新規追加 (START) ---
        # 1000px 推定: normal_price_group (Y=370) の上。
        self.price_type_params={'font_path':self.font_path_noto_sans_black, 'font_color':self.WHITE, 'x1':0, 'y1':310, 'x2':1000, 'y2':360, 'align':'center'}
        # --- 新規追加 (END) ---
        
        self.normal_price_group={
            'price': {'text':'','font_path':self.font_path_reddit,'font_size':130,'font_color':self.WHITE,'x_origin':0,'x_end':self.width,'y_origin':370},
            'unit':  {'text':'円','font_path':self.font_path_noto_sans_black,'font_size':70,'font_color':self.WHITE,'dy':35},
            'suffix':{'text':'のところ','font_path':self.font_path_noto_sans_black,'font_size':50,'font_color':self.WHITE,'dy':65}
        }
        self.discount_group={
             'price': {'text':'','font_path':self.font_path_reddit,'font_size':95,'font_color':self.RED,'x_origin':0,'x_end':self.width,'y_origin':540},
             'unit':  {'text':'','font_path':self.font_path_noto_sans_black,'font_size':60,'font_color':self.RED,'dy':20},
             'suffix':{'text':'OFF','font_path':self.font_path_noto_sans_black,'font_size':40,'font_color':self.RED,'dy':45}
        }
        self.sale_price_group={
            'price': {'text':'','font_path':self.font_path_reddit,'font_size':230,'font_color':self.YELLOW,'x_origin':0,'x_end':self.width,'y_origin':660},
            'unit':  {'text':'円','font_path':self.font_path_noto_sans_black,'font_size':70,'font_color':self.YELLOW,'dy':130},
            'suffix':{'text':'税込','font_path':self.font_path_noto_sans_black,'font_size':30,'font_color':self.YELLOW,'dy':100}
        }
    def _draw_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        self._place_text(draw, {**self.start_datetime_params, 'text': self._format_datetime_jp(row_data.startDate)})
        self._place_text(draw, {**self.end_datetime_params, 'text': self._format_datetime_jp(row_data.endDate)})
        # -----------------------------------------
        self._place_text(draw, {**self.message_params, 'text': row_data.saleText or ""})
        
        # --- 新規追加 (START) ---
        self._place_text(draw, {**self.price_type_params, 'text': row_data.priceType or ""})
        # --- 新規追加 (END) ---

        self.normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        self.sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        self.discount_group['price']['text'] = discount_number
        self.discount_group['unit']['text'] = discount_unit_text
        self._place_price_group(draw, self.normal_price_group['price'], self.normal_price_group['unit'], self.normal_price_group['suffix'])
        self._place_price_group(draw, self.discount_group['price'], self.discount_group['unit'], self.discount_group['suffix'])
        self._place_price_group(draw, self.sale_price_group['price'], self.sale_price_group['unit'], self.sale_price_group['suffix'])
factory_registry.register_factory('B', FactoryTypeB)

class FactoryTypeB2(FactoryTypeB):
    def __init__(self):
        super().__init__()
        # --- 上書き (START) ---
        # Yシフト +45 (RTF 768px に基づく: 390 - 345 = 45)
        self.price_type_params={'font_path':self.font_path_noto_sans_black, 'font_color':self.WHITE, 'x1':0, 'y1':310, 'x2':1000, 'y2':360, 'align':'center'}
        # --- 上書き (END) ---
    
    # _draw_details は継承され、上書きされた self.price_type_params を自動的に使用します。
    pass
factory_registry.register_factory('B-2', FactoryTypeB2)

class FactoryTypeC(BaseImageFactory):
    def __init__(self):
        super().__init__()
        self.width, self.height = 1000, 1000
        self.YELLOW=(235, 210, 150); self.RED=(150,0,0)
        self.start_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.WHITE,'x1':25,'y1':187,'x2':465,'y2':252,'align':'right'}
        self.end_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.WHITE,'x1':530,'y1':187,'x2':960,'y2':252,'align':'left'}
        self.message_params={'font_path':self.font_path_shippori_bold,'font_color':self.WHITE,'x1':107,'y1':38,'x2':894,'y2':170,'align':'center'}
        
        # --- 新規追加 (START) ---
        # 1000px 推定: normal_price_group (Y=360) の上。
        self.price_type_params={'font_path':self.font_path_shippori_bold, 'font_color':self.WHITE, 'x1':0, 'y1':310, 'x2':1000, 'y2':360, 'align':'center'}
        # --- 新規追加 (END) ---

        self.normal_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':130,'font_color':self.WHITE,'x_origin':0,'x_end':self.width,'y_origin':360},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':self.WHITE,'dy':65},
            'suffix':{'text':'のところ','font_path':self.font_path_shippori_bold,'font_size':50,'font_color':self.WHITE,'dy':95}
        }
        self.discount_group={
             'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':95,'font_color':self.RED,'x_origin':0,'x_end':self.width,'y_origin':530},
             'unit':  {'text':'','font_path':self.font_path_shippori_bold,'font_size':60,'font_color':self.RED,'dy':40},
             'suffix':{'text':'OFF','font_path':self.font_path_shippori_bold,'font_size':40,'font_color':self.RED,'dy':65}
        }
        self.sale_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':200,'font_color':self.YELLOW,'x_origin':0,'x_end':self.width,'y_origin':650},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':self.YELLOW,'dy':145},
            'suffix':{'text':'税込','font_path':self.font_path_shippori_bold,'font_size':30,'font_color':self.YELLOW,'dy':115}
        }
    def _draw_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        self._place_text(draw, {**self.start_datetime_params, 'text': self._format_datetime_jp(row_data.startDate)})
        self._place_text(draw, {**self.end_datetime_params, 'text': self._format_datetime_jp(row_data.endDate)})
        # -----------------------------------------
        self._place_text(draw, {**self.message_params, 'text': row_data.saleText or ""})

        # --- 新規追加 (START) ---
        self._place_text(draw, {**self.price_type_params, 'text': row_data.priceType or ""})
        # --- 新規追加 (END) ---

        self.normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        self.sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        self.discount_group['price']['text'] = discount_number
        self.discount_group['unit']['text'] = discount_unit_text
        self._place_price_group(draw, self.normal_price_group['price'], self.normal_price_group['unit'], self.normal_price_group['suffix'])
        self._place_price_group(draw, self.discount_group['price'], self.discount_group['unit'], self.discount_group['suffix'])
        self._place_price_group(draw, self.sale_price_group['price'], self.sale_price_group['unit'], self.sale_price_group['suffix'])
factory_registry.register_factory('C', FactoryTypeC)

class FactoryTypeC2(FactoryTypeC):
    def __init__(self):
        super().__init__()
        # --- 上書き (START) ---
        # Yシフト +75 (RTF 768px に基づく: 435 - 360 = 75)
        self.price_type_params={'font_path':self.font_path_shippori_bold, 'font_color':self.WHITE, 'x1':0, 'y1':300+35, 'x2':1000, 'y2':350+35, 'align':'center'}
        # --- 上書き (END) ---
    pass
factory_registry.register_factory('C-2', FactoryTypeC2)

class FactoryTypeD(BaseImageFactory):
    def __init__(self):
        super().__init__()
        # ... (Factory D のパラメータは変更なし) ...
        self.width, self.height = 1000, 1000
        self.BROWN=(90,70,50); self.RED=(215,0,0)
        self.start_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':25,'y1':187,'x2':465,'y2':252,'align':'right'}
        self.end_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':530,'y1':187,'x2':960,'y2':252,'align':'left'}
        self.message_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':107,'y1':38,'x2':894,'y2':170,'align':'center'}

        # --- 新規追加 (START) ---
        # 1000px 推定: normal_price_group (Y=380) の上。
        self.price_type_params={'font_path':self.font_path_noto_sans_black, 'font_color':self.BROWN, 'x1':0, 'y1':315, 'x2':1000, 'y2':370, 'align':'center'}
        # --- 新規追加 (END) ---
        
        self.normal_price_group={
            'price': {'text':'','font_path':self.font_path_public_sans_bold,'font_size':130,'font_color':self.BROWN,'x_origin':0,'x_end':self.width,'y_origin':380},
            'unit':  {'text':'円','font_path':self.font_path_noto_sans_black,'font_size':70,'font_color':self.BROWN,'dy':35},
            'suffix':{'text':'のところ','font_path':self.font_path_noto_sans_black,'font_size':50,'font_color':self.BROWN,'dy':60}
        }
        self.discount_group={
             'price': {'text':'','font_path':self.font_path_public_sans_bold,'font_size':85,'font_color':self.WHITE,'x_origin':0,'x_end':self.width,'y_origin':550},
             'unit':  {'text':'','font_path':self.font_path_noto_sans_black,'font_size':50,'font_color':self.WHITE,'dy':15},
             'suffix':{'text':'OFF','font_path':self.font_path_noto_sans_black,'font_size':30,'font_color':self.WHITE,'dy':40}
        }
        self.sale_price_group={
            'price': {'text':'','font_path':self.font_path_public_sans_bold,'font_size':200,'font_color':self.RED,'x_origin':0,'x_end':self.width,'y_origin':700},
            'unit':  {'text':'円','font_path':self.font_path_noto_sans_black,'font_size':70,'font_color':self.RED,'dy':95},
            'suffix':{'text':'税込','font_path':self.font_path_noto_sans_black,'font_size':30,'font_color':self.RED,'dy':65}
        }
    def _draw_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        self._place_text(draw, {**self.start_datetime_params, 'text': self._format_datetime_jp(row_data.startDate)})
        self._place_text(draw, {**self.end_datetime_params, 'text': self._format_datetime_jp(row_data.endDate)})
        # -----------------------------------------
        self._place_text(draw, {**self.message_params, 'text': row_data.saleText or ""})

        # --- 新規追加 (START) ---
        self._place_text(draw, {**self.price_type_params, 'text': row_data.priceType or ""})
        # --- 新規追加 (END) ---

        self.normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        self.sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        self.discount_group['price']['text'] = discount_number
        self.discount_group['unit']['text'] = discount_unit_text
        self._place_price_group(draw, self.normal_price_group['price'], self.normal_price_group['unit'], self.normal_price_group['suffix'])
        self._place_price_group(draw, self.discount_group['price'], self.discount_group['unit'], self.discount_group['suffix'])
        self._place_price_group(draw, self.sale_price_group['price'], self.sale_price_group['unit'], self.sale_price_group['suffix'])
factory_registry.register_factory('D', FactoryTypeD)

class FactoryTypeD2(FactoryTypeD):
    def __init__(self):
        super().__init__()
        # --- 上書き (START) ---
        # Yシフト +20 (RTF 768px に基づく)
        self.price_type_params={'font_path':self.font_path_noto_sans_black, 'font_color':self.BROWN, 'x1':0, 'y1':315+20, 'x2':1000, 'y2':370+20, 'align':'center'}
        # --- 上書き (END) ---
    pass
factory_registry.register_factory('D-2', FactoryTypeD2)

class FactoryTypeE(BaseImageFactory):
    def __init__(self):
        super().__init__()
        # ... (Factory E のパラメータは変更なし) ...
        self.width, self.height = 1000, 1000
        self.SILVER=(204,204,204); self.GOLD=(235, 210, 150)
        self.start_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.BLACK,'x1':25,'y1':200,'x2':465,'y2':265,'align':'right'}
        self.end_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.BLACK,'x1':530,'y1':200,'x2':960,'y2':265,'align':'left'}
        self.message_params={'font_path':self.font_path_shippori_bold,'font_color':self.BLACK,'x1':107,'y1':38,'x2':894,'y2':170,'align':'center'}

        # --- 新規追加 (START) ---
        # 1000px 推定: normal_price_group (Y=360) の上。
        self.price_type_params={'font_path':self.font_path_shippori_bold, 'font_color':self.SILVER, 'x1':0, 'y1':325, 'x2':1000, 'y2':385, 'align':'center'}
        # --- 新規追加 (END) ---
        
        self.normal_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':130,'font_color':self.SILVER,'x_origin':0,'x_end':self.width,'y_origin':360},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':self.SILVER,'dy':65},
            'suffix':{'text':'のところ','font_path':self.font_path_shippori_bold,'font_size':50,'font_color':self.SILVER,'dy':95}
        }
        self.discount_params={
            'font_path':self.font_path_shippori_bold,
            'font_color':self.GOLD,
            'x1': 645, 'y1': 620, 'x2': 965, 'y2': 670,
            'align':'center'
        }
        self.sale_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':200,'font_color':self.GOLD,'x_origin':0,'x_end':self.width,'y_origin':650},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':self.GOLD,'dy':145},
            'suffix':{'text':'税込','font_path':self.font_path_shippori_bold,'font_size':30,'font_color':self.GOLD,'dy':115}
        }
    def _draw_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        self._place_text(draw, {**self.start_datetime_params, 'text': self._format_datetime_jp(row_data.startDate)})
        self._place_text(draw, {**self.end_datetime_params, 'text': self._format_datetime_jp(row_data.endDate)})
        # -----------------------------------------
        self._place_text(draw, {**self.message_params, 'text': row_data.saleText or ""})

        # --- 新規追加 (START) ---
        self._place_text(draw, {**self.price_type_params, 'text': row_data.priceType or ""})
        # --- 新規追加 (END) ---

        self.normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        self.sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_display_text = ""
        if discount_text_val:
         discount_number = discount_text_val.replace('%', '').replace('円', '')
         if '%' in discount_text_val:
             discount_display_text = f"{discount_number}%OFF"
         elif '円' in discount_text_val:
             discount_display_text = f"{discount_number}円OFF"
        self._place_text(draw, {**self.discount_params, 'text': discount_display_text})
        self._place_price_group(draw, self.normal_price_group['price'], self.normal_price_group['unit'], self.normal_price_group['suffix'])
        self._place_price_group(draw, self.sale_price_group['price'], self.sale_price_group['unit'], self.sale_price_group['suffix'])
factory_registry.register_factory('E', FactoryTypeE)

class FactoryTypeE2(FactoryTypeE):
    def __init__(self):
        super().__init__()
        # --- 上書き (START) ---
        # Yシフト +45 (コード 290+45 に基づく)
        self.price_type_params={'font_path':self.font_path_shippori_bold, 'font_color':self.SILVER, 'x1':0, 'y1':290+45, 'x2':1000, 'y2':350+45, 'align':'center'}
        # --- 上書き (END) ---
    pass
factory_registry.register_factory('E-2', FactoryTypeE2)

class FactoryTypeF(BaseImageFactory):
    def __init__(self):
        super().__init__()
        # ... (Factory F のパラメータは変更なし) ...
        self.width, self.height = 1000, 1000
        self.BLACK=(93, 95, 96); self.GOLD=(210, 172, 67)
        self.start_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.GOLD,'x1':25,'y1':187,'x2':465,'y2':252,'align':'right'}
        self.end_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.GOLD,'x1':530,'y1':187,'x2':960,'y2':252,'align':'left'}
        self.message_params={'font_path':self.font_path_shippori_bold,'font_color':self.GOLD,'x1':107,'y1':38,'x2':894,'y2':170,'align':'center'}
        
        # --- 新規追加 (START) ---
        # 1000px 推定: normal_price_group (Y=360) の上。
        self.price_type_params={'font_path':self.font_path_shippori_bold, 'font_color':self.BLACK, 'x1':0, 'y1':320, 'x2':1000, 'y2':370, 'align':'center'}
        # --- 新規追加 (END) ---

        self.normal_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':130,'font_color':self.BLACK,'x_origin':0,'x_end':self.width,'y_origin':360},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':self.BLACK,'dy':65},
            'suffix':{'text':'のところ','font_path':self.font_path_shippori_bold,'font_size':50,'font_color':self.BLACK,'dy':95}
        }
        self.discount_group={
             'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':95,'font_color':self.WHITE,'x_origin':0,'x_end':self.width,'y_origin':530},
             'unit':  {'text':'','font_path':self.font_path_shippori_bold,'font_size':60,'font_color':self.WHITE,'dy':40},
             'suffix':{'text':'OFF','font_path':self.font_path_shippori_bold,'font_size':40,'font_color':self.WHITE,'dy':65}
        }
        self.sale_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':200,'font_color':self.GOLD,'x_origin':0,'x_end':self.width,'y_origin':650},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':self.GOLD,'dy':145},
            'suffix':{'text':'税込','font_path':self.font_path_shippori_bold,'font_size':30,'font_color':self.GOLD,'dy':115}
        }
    def _draw_details(self, draw: ImageDraw, row_data: Tool03ProductRowInput):
        self._place_text(draw, {**self.start_datetime_params, 'text': self._format_datetime_jp(row_data.startDate)})
        self._place_text(draw, {**self.end_datetime_params, 'text': self._format_datetime_jp(row_data.endDate)})
        # -----------------------------------------
        self._place_text(draw, {**self.message_params, 'text': row_data.saleText or ""})

        # --- 新規追加 (START) ---
        self._place_text(draw, {**self.price_type_params, 'text': row_data.priceType or ""})
        # --- 新規追加 (END) ---

        self.normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        self.sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        self.discount_group['price']['text'] = discount_number
        self.discount_group['unit']['text'] = discount_unit_text
        self._place_price_group(draw, self.normal_price_group['price'], self.normal_price_group['unit'], self.normal_price_group['suffix'])
        self._place_price_group(draw, self.discount_group['price'], self.discount_group['unit'], self.discount_group['suffix'])
        self._place_price_group(draw, self.sale_price_group['price'], self.sale_price_group['unit'], self.sale_price_group['suffix'])
factory_registry.register_factory('F', FactoryTypeF)

class FactoryTypeF2(FactoryTypeF):
    def __init__(self):
        super().__init__()
        # --- 上書き (START) ---
        # Yシフト +40 (コード 290+40, 350+40 に基づく)
        self.price_type_params={'font_path':self.font_path_shippori_bold, 'font_color':self.BLACK, 'x1':0, 'y1':290+40, 'x2':1000, 'y2':350+40, 'align':'center'}
        # --- 上書き (END) ---
    pass
factory_registry.register_factory('F-2', FactoryTypeF2)

# === メインサービス (バックグラウンドタスク - POST) ===
async def generate_images_background(job_id: str, product_rows: List[Tool03ProductRowInput]):
    # ... (ジョブログic部分は変更なし) ...
    logging.info(f"[Job {job_id}] {len(product_rows)} 件の画像の処理を開始します。")
    job_dir = JOB_STORAGE_BASE_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    start_time = time.time()
    initial_job_data: Dict[str, Any] = {
        "status": "Processing", "progress": 0, "total": len(product_rows),
        "results": {}, "startTime": start_time, "endTime": None, "message": None,
        "ftpUploadStatusGold": "idle", "ftpUploadErrorGold": None,
        "ftpUploadStatusRcabinet": "idle", "ftpUploadErrorRcabinet": None,
    }
    job_tracker[job_id] = initial_job_data
    error_count = 0
    final_status = "Processing"
    try:
        for index, row in enumerate(product_rows):
            logging.debug(f"[Job {job_id}] 画像 {index + 1}/{len(product_rows)} を処理中: {row.productCode}")
            row_id = row.id
            current_result_dict = Tool03ImageResult(status="Pending").model_dump()
            if job_id in job_tracker:
                 job_tracker[job_id]["results"][row_id] = current_result_dict
            else:
                 logging.warning(f"[Job {job_id}] 行 {index+1} の開始前に Job がトラッカーに存在しません")
                 return
            template_name = row.template or "テンプレートA"
            base_key = template_name.replace("テンプレート", "")
            factory_key = base_key
            has_mobile_data = bool(row.mobileStartDate and row.mobileEndDate)
            potential_mobile_key = f"{base_key}-2"
            if has_mobile_data and potential_mobile_key in factory_registry._factories:
                factory_key = potential_mobile_key
            logging.debug(f"[Job {job_id}] 行 {index+1} を処理中:")
            logging.debug(f"  - 受信テンプレート名: '{row.template}'")
            logging.debug(f"  - 計算された base_key: '{base_key}'")
            logging.debug(f"  - 最終 factory_key: '{factory_key}'")
            try:
                 current_result_dict["status"] = "Processing"
                 if job_id in job_tracker:
                      job_tracker[job_id]["results"][row_id] = current_result_dict
                 factory = factory_registry.get_factory(factory_key)
                 img: Image.Image = factory.draw(row, factory_key)
                 output_filename = f"{row.productCode}.jpg"
                 output_path = job_dir / output_filename
                 img.save(output_path, "JPEG", quality=95)
                 current_result_dict["status"] = "Success"
                 current_result_dict["filename"] = output_filename
                 img.close()
            except (FileNotFoundError, ValueError, NotImplementedError) as e:
                logging.error(f"[Job {job_id}] 画像 {index + 1} ({row.productCode}, テンプレート '{factory_key}') の処理エラー: {e}")
                current_result_dict["status"] = "Error"
                current_result_dict["message"] = str(e)
                error_count += 1
            except Exception as draw_error:
                logging.error(f"[Job {job_id}] 画像 {index + 1} ({row.productCode}, テンプレート '{factory_key}') の描画中に不明なエラー: {draw_error}", exc_info=True)
                current_result_dict["status"] = "Error"
                current_result_dict["message"] = "画像描画中に不明なエラーが発生しました。"
                error_count += 1
            finally:
                if job_id in job_tracker:
                    job_tracker[job_id]["results"][row_id] = current_result_dict
                    job_tracker[job_id]["progress"] = len([
                         res for res in job_tracker[job_id]["results"].values()
                         if res.get("status") in ["Success", "Error"]
                    ])
                else:
                    logging.warning(f"[Job {job_id}] 行 {index+1} の処理完了時に Job がトラッカーに存在しません")
            await asyncio.sleep(0.01)
        if job_id in job_tracker:
            final_status = "Completed" if error_count == 0 else "Completed with errors"
            logging.info(f"[Job {job_id}] 処理完了。ステータス: {final_status}。エラー: {error_count}/{len(product_rows)}。")
    except Exception as e:
        final_status = "Failed"
        logging.error(f"[Job {job_id}] バックグラウンドタスクで重大なエラーが発生: {e}", exc_info=True)
        if job_id in job_tracker:
             job_tracker[job_id]["message"] = f"システムエラー: {e}"
    finally:
        if job_id in job_tracker:
            end_time = time.time()
            job_tracker[job_id]["status"] = final_status
            job_tracker[job_id]["endTime"] = end_time
            logging.info(f"[Job {job_id}] 処理時間: {end_time - start_time:.2f} 秒。")

# === ジョブステータス取得関数 ===
def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    return job_tracker.get(job_id)

# --- ZIP 作成関数 ---
def create_job_zip_archive(job_id: str) -> Optional[str]:
    job_dir = JOB_STORAGE_BASE_DIR / job_id
    if not job_dir.is_dir():
        logging.error(f"Job ディレクトリが存在しません: {job_dir}")
        raise FileNotFoundError("Job ディレクトリが見つかりません。")
    temp_dir = tempfile.gettempdir()
    zip_filename_base = f"tool03_images_{job_id}"
    zip_output_path_base = os.path.join(temp_dir, zip_filename_base)
    try:
        zip_path = shutil.make_archive(
            base_name=zip_output_path_base,
            format='zip',
            root_dir=str(job_dir)
        )
        logging.info(f"Zip ファイルの作成に成功: {zip_path}")
        return zip_path
    except Exception as e:
        logging.error(f"Job {job_id} の Zip ファイル作成中にエラー: {e}", exc_info=True)
        zip_file = f"{zip_output_path_base}.zip"
        if os.path.exists(zip_file):
            try: os.remove(zip_file)
            except OSError as remove_e: logging.error(f"エラーが発生した一時 Zip ファイルを削除できません: {zip_file}, エラー: {remove_e}")
        raise Exception("Zip ファイルの作成に失敗しました。") from e

# === 画像再生成バックグラウンドタスク (PATCH) ===
async def regenerate_specific_images_background(job_id: str, modified_rows: List[Tool03ProductRowInput]):
    logging.info(f"[Job {job_id}] {len(modified_rows)} 件の画像の再生成/追加を開始します。")
    current_job_data = job_tracker.get(job_id)
    if not current_job_data:
        logging.error(f"[Job {job_id}] 画像再生成のための Job が見つかりません (ロジックエラー?)。")
        return
    job_dir = JOB_STORAGE_BASE_DIR / job_id
    if not job_dir.is_dir():
         logging.error(f"[Job {job_id}] Job ディレクトリが存在しません: {job_dir}")
         current_job_data["status"] = "Failed"
         current_job_data["message"] = "画像ストレージディレクトリが失われました。"
         return
    current_total = current_job_data.get("total", 0)
    new_rows_count = 0
    for row in modified_rows:
        if row.id not in current_job_data["results"]:
            new_rows_count += 1
            current_job_data["results"][row.id] = Tool03ImageResult(status="Pending").model_dump()
    if new_rows_count > 0:
        updated_total = len(current_job_data["results"])
        current_job_data["total"] = updated_total
        logging.info(f"[Job {job_id}] {new_rows_count} 件の新規行を検出。total を {updated_total} に更新しました。")
    current_job_data["status"] = "Processing"
    current_job_data["message"] = None
    current_job_data["endTime"] = None
    current_job_data["ftpUploadStatusGold"] = "idle"
    current_job_data["ftpUploadErrorGold"] = None
    current_job_data["ftpUploadStatusRcabinet"] = "idle"
    current_job_data["ftpUploadErrorRcabinet"] = None
    final_status = "Processing"
    try:
        for index, row in enumerate(modified_rows):
            row_id = row.id
            logging.debug(f"[Job {job_id}] 画像 {index + 1}/{len(modified_rows)} を再生成/追加中 (Row ID: {row_id}, {row.productCode})")
            current_result_dict = current_job_data["results"].get(row_id, Tool03ImageResult(status="Pending").model_dump())
            current_result_dict["status"] = "Processing"
            current_result_dict["message"] = None
            current_result_dict["filename"] = None
            current_job_data["results"][row_id] = current_result_dict
            template_name = row.template or "テンプレートA"
            base_key = template_name.replace("テンプレート", "")
            factory_key = base_key
            has_mobile_data = bool(row.mobileStartDate and row.mobileEndDate)
            potential_mobile_key = f"{base_key}-2"
            if has_mobile_data and potential_mobile_key in factory_registry._factories:
                factory_key = potential_mobile_key
            try:
                factory = factory_registry.get_factory(factory_key)
                img: Image.Image = factory.draw(row, factory_key)
                output_filename = f"{row.productCode}.jpg"
                output_path = job_dir / output_filename
                img.save(output_path, "JPEG", quality=95)
                current_result_dict["status"] = "Success"
                current_result_dict["filename"] = output_filename
                img.close()
            except (FileNotFoundError, ValueError, NotImplementedError) as e:
                logging.error(f"[Job {job_id}] 画像の再生成/追加エラー ({row.productCode}, テンプレート '{factory_key}'): {e}")
                current_result_dict["status"] = "Error"
                current_result_dict["message"] = str(e)
            except Exception as draw_error:
                logging.error(f"[Job {job_id}] 画像の再生成/追加中に不明なエラー ({row.productCode}, テンプレート '{factory_key}'): {draw_error}", exc_info=True)
                current_result_dict["status"] = "Error"
                current_result_dict["message"] = "画像描画中に不明なエラーが発生しました。"
            finally:
                 if job_id in job_tracker:
                     job_tracker[job_id]["results"][row_id] = current_result_dict
                     job_tracker[job_id]["progress"] = len([
                          res for res in job_tracker[job_id]["results"].values()
                          if res.get("status") in ["Success", "Error"]
                     ])
                 else:
                     logging.warning(f"[Job {job_id}] 再生成 Row {row_id} の処理完了時に Job がトラッカーに存在しません")
            await asyncio.sleep(0.01)
        if job_id in job_tracker:
             completed_count = 0
             has_errors = False
             for res_dict in job_tracker[job_id]["results"].values():
                  res = Tool03ImageResult(**res_dict)
                  if res.status == "Error":
                       has_errors = True
                  if res.status in ["Success", "Error"]:
                      completed_count += 1
             job_tracker[job_id]["progress"] = completed_count
             current_total = job_tracker[job_id]["total"]
             if completed_count == current_total:
                 if has_errors:
                      final_status = "Completed with errors"
                 else:
                      final_status = "Completed"
                 logging.info(f"[Job {job_id}] 画像の再生成/追加完了。最終ステータス: {final_status}。進捗: {completed_count}/{current_total}。")
             else:
                  final_status = "Processing"
                  logging.debug(f"[Job {job_id}] ジョブはまだ処理中です。進捗: {completed_count}/{current_total}")
        else:
             final_status = "Failed"
    except Exception as e:
        final_status = "Failed"
        logging.error(f"[Job {job_id}] 画像の再生成/追加中に重大なエラーが発生: {e}", exc_info=True)
        if job_id in job_tracker:
            job_tracker[job_id]["message"] = f"画像の再生成/追加中にシステムエラー: {e}"
    finally:
        if job_id in job_tracker and final_status != "Processing":
            end_time = time.time()
            job_tracker[job_id]["status"] = final_status
            job_tracker[job_id]["endTime"] = end_time

# === FTP アップロード関数 ===
def upload_job_images_to_ftp(job_id: str, target: str):
    # ... (FTPロジック部分は変更なし) ...
    ftp_configs = {
        "gold": {
            "host": "ftp.rakuten.ne.jp", "port": 16910, "user": "auc-ronnefeldt",
            "password": "Ronne@04", "remote_dir": "/public_html/tools/03/"
        },
        "rcabinet": {
             "host": "upload.rakuten.ne.jp", "port": 16910, "user": "auc-ronnefeldt",
             "password": "Ronne@04", "remote_dir": "/images/"
        }
    }
    config = ftp_configs.get(target)
    if not config:
        logging.error(f"[Job {job_id}] ターゲット '{target}' の FTP 設定が見つかりません")
        if job_id in job_tracker:
            ftp_status_key = f"ftpUploadStatus{target.capitalize()}"
            ftp_error_key = f"ftpUploadError{target.capitalize()}"
            job_tracker[job_id][ftp_status_key] = "failed"
            job_tracker[job_id][ftp_error_key] = f"FTP 設定 '{target}' が見つかりません。"
        return
    job_dir = JOB_STORAGE_BASE_DIR / job_id
    if not job_dir.is_dir():
        logging.error(f"[Job {job_id}] アップロード対象の Job ディレクトリが存在しません: {job_dir}")
        if job_id in job_tracker:
            ftp_status_key = f"ftpUploadStatus{target.capitalize()}"
            ftp_error_key = f"ftpUploadError{target.capitalize()}"
            job_tracker[job_id][ftp_status_key] = "failed"
            job_tracker[job_id][ftp_error_key] = "画像を含むディレクトリが存在しません。"
        return
    logging.info(f"[Job {job_id}] FTP ターゲット '{target}' (ホスト: {config['host']}) へのアップロードを開始します。")
    ftp_status_key = f"ftpUploadStatus{target.capitalize()}"
    ftp_error_key = f"ftpUploadError{target.capitalize()}"
    upload_status = "failed"
    upload_error_msg = None
    if job_id in job_tracker:
         job_tracker[job_id][ftp_status_key] = "uploading"
         job_tracker[job_id][ftp_error_key] = None
    else:
         logging.warning(f"[Job {job_id}] FTP アップロード開始時に Job がトラッカーに存在しません。")
         return
    ftp = None
    try:
        ftp = ftplib.FTP()
        ftp.connect(config['host'], config['port'], timeout=30)
        ftp.login(config['user'], config['password'])
        ftp.set_pasv(True)
        logging.info(f"[Job {job_id}] FTP ディレクトリに移動中: {config['remote_dir']}")
        try:
             ftp.cwd(config['remote_dir'])
        except ftplib.error_perm as e:
             if "550" in str(e):
                  try:
                       logging.warning(f"[Job {job_id}] ディレクトリ {config['remote_dir']} が存在しません。作成を試みます...")
                       parts = Path(config['remote_dir']).parts
                       current_dir = "/"
                       for part in parts:
                           if not part or part == "/": continue
                           current_dir = os.path.join(current_dir, part)
                           try:
                               ftp.mkd(current_dir)
                               logging.debug(f"[Job {job_id}] FTP ディレクトリを作成しました: {current_dir}")
                           except ftplib.error_perm as mkd_e:
                               if "550" not in str(mkd_e):
                                   raise
                       ftp.cwd(config['remote_dir'])
                       logging.info(f"[Job {job_id}] ディレクトリを作成し、{config['remote_dir']} に移動しました")
                  except ftplib.all_errors as mkd_e:
                       upload_error_msg = f"FTP ディレクトリ '{config['remote_dir']}' の作成/移動に失敗しました: {mkd_e}"
                       logging.error(f"[Job {job_id}] {upload_error_msg}", exc_info=True)
                       raise
             else:
                  upload_error_msg = f"FTP ディレクトリ '{config['remote_dir']}' へのアクセス権エラー: {e}"
                  logging.error(f"[Job {job_id}] {upload_error_msg}", exc_info=True)
                  raise
        image_files_to_upload = []
        if job_id in job_tracker and "results" in job_tracker[job_id]:
             for result_data in job_tracker[job_id]["results"].values():
                 res = Tool03ImageResult(**result_data)
                 if res.status == "Success" and res.filename and (job_dir / res.filename).is_file():
                     image_files_to_upload.append(res.filename)
        successful_uploads = 0
        total_to_upload = len(image_files_to_upload)
        upload_errors = []
        if not image_files_to_upload:
             logging.warning(f"[Job {job_id}] {target} にアップロードする正常な画像がありません。")
             upload_status = "success"
        for filename in image_files_to_upload:
            local_path = job_dir / filename
            remote_path = filename
            try:
                with open(local_path, 'rb') as file:
                    ftp.storbinary(f'STOR {remote_path}', file)
                    logging.info(f"[Job {job_id}] ファイルのアップロードに成功: {filename} -> {target}")
                    successful_uploads += 1
            except ftplib.all_errors as upload_e:
                 err_msg = f"ファイル {filename} のアップロードエラー: {upload_e}"
                 logging.error(f"[Job {job_id}] {err_msg}", exc_info=True)
                 upload_errors.append(err_msg)
        if successful_uploads == total_to_upload:
             upload_status = "success"
             logging.info(f"[Job {job_id}] アップロード完了。成功: {successful_uploads}/{total_to_upload} ファイル (ターゲット: {target})。")
        else:
             upload_status = "failed"
             upload_error_msg = f"{total_to_upload - successful_uploads}/{total_to_upload} ファイルのアップロードに失敗しました。"
             if upload_errors:
                 upload_error_msg += f" エラー例: {upload_errors[0]}"
             logging.error(f"[Job {job_id}] {upload_error_msg}")
    except ftplib.all_errors as e:
        upload_error_msg = f"FTP 接続/認証エラー ({target}): {e}"
        logging.error(f"[Job {job_id}] {upload_error_msg}", exc_info=True)
    except Exception as e:
        upload_error_msg = f"FTP アップロード中に不明なエラー ({target}): {e}"
        logging.error(f"[Job {job_id}] {upload_error_msg}", exc_info=True)
    finally:
        if ftp:
            try: ftp.quit()
            except ftplib.all_errors: pass
        if job_id in job_tracker:
            job_tracker[job_id][ftp_status_key] = upload_status
            job_tracker[job_id][ftp_error_key] = upload_error_msg
            logging.info(f"[Job {job_id}] FTP ステータス '{target}' を '{upload_status}' に更新しました。")

# === 古いジョブのクリーンアップ関数 ===
async def cleanup_old_jobs():
     current_time = time.time()
     timeout = 3600
     jobs_to_delete = [
          job_id for job_id, data in list(job_tracker.items())
          if current_time - (data.get("endTime") or data.get("startTime", 0)) > timeout
     ]
     if jobs_to_delete:
          logging.info(f"{len(jobs_to_delete)} 件の古いジョブのクリーンアップを準備中。")
          for job_id in jobs_to_delete:
               logging.info(f"古いジョブをクリーンアップ中: {job_id}")
               try:
                    job_tracker.pop(job_id, None)
                    job_dir = JOB_STORAGE_BASE_DIR / job_id
                    if job_dir.exists():
                         shutil.rmtree(job_dir)
               except Exception as e:
                    logging.error(f"Job {job_id} のクリーンアップ中にエラー: {e}")
     await asyncio.sleep(600)
     asyncio.create_task(cleanup_old_jobs())

