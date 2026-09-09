"""Category matching and auto-creation for imported bank transactions."""

from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from decimal import Decimal
import re

_CHARACTER_TRANSLATION = str.maketrans({
    'ي': 'ی', 'ى': 'ی', 'ك': 'ک',
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
})


def normalize_text(value: str) -> str:
    """Normalize Persian/Arabic spelling, digits, whitespace and case."""
    if not value:
        return ''
    return ' '.join(str(value).translate(_CHARACTER_TRANSLATION).casefold().split())


@dataclass(frozen=True)
class CategoryRule:
    """Rule for matching and auto-creating categories."""
    kind: str  # 'income' or 'expense'
    keywords: Tuple[str, ...]  # keywords to match in description
    category_name: str  # name to create if not exists
    category_color: str = '#6C63FF'  # default color


# ============================================================
# CATEGORY RULES - در صورت عدم وجود، ساخته می‌شوند
# ============================================================

CATEGORY_RULES = (
    # Expense rules
    CategoryRule('expense', ('اسنپ', 'تپسی'), 'حمل و نقل', '#FF6B6B'),
    CategoryRule('expense', ('دیجی کالا', 'دیجیکالا'), 'خرید کالا', '#4ECDC4'),
    CategoryRule('expense', ('کافه بازار', 'مایکت'), 'نرم‌افزار و اشتراک', '#45B7D1'),
    CategoryRule('expense', ('قبض', 'آب و فاضلاب', 'برق', 'گاز'), 'قبوض', '#FFA07A'),
    CategoryRule('expense', ('داروخانه', 'بیمارستان', 'درمان'), 'درمان و سلامت', '#98D8C8'),
    CategoryRule('expense', ('سوپرمارکت', 'مواد غذایی', 'میوه'), 'مواد غذایی', '#F7DC6F'),
    CategoryRule('expense', ('رستوران', 'کافه', 'اسنپ فود', 'snappfood'), 'رستوران و کافه', '#F1948A'),
    CategoryRule('expense', ('نانوایی', 'نان'), 'نانوایی', '#D4A574'),
    CategoryRule('expense', ('شارژ', 'سامانه موبايل بانک'), 'شارژ تلفن', '#85C1E9'),
    CategoryRule('expense', ('انتقال', 'کارت به کارت', 'شتابی'), 'انتقال وجه', '#BB8FCE'),
    CategoryRule('expense', ('کارمزد', 'کمیسیون'), 'کارمزد بانکی', '#F5B7B1'),
    CategoryRule('expense', ('پرداخت قسط', 'تسهیلات'), 'اقساط و تسهیلات', '#F8C471'),
    CategoryRule('expense', ('خريد کالا و خدمات', 'خرید', 'کالا'), 'خرید کالا', '#82E0AA'),
    CategoryRule('expense', ('ارز', 'دلار', 'یورو'), 'تبدیل ارز', '#AED6F1'),

    # Income rules
    CategoryRule('income', ('حقوق', 'دستمزد'), 'حقوق و دستمزد', '#2ECC71'),
    CategoryRule('income', ('سود سپرده', 'سود'), 'سود سرمایه‌گذاری', '#F1C40F'),
    CategoryRule('income', ('پایا', 'واریز پایا'), 'واریز پایا', '#3498DB'),
    CategoryRule('income', ('سپرده گذاری مرکزی', 'لوتوس'), 'سود اوراق بهادار', '#9B59B6'),
    CategoryRule('income', ('انتقال وجه داخلی', 'دریافت وجه'), 'انتقال وجه دریافتی', '#1ABC9C'),
    CategoryRule('income', ('کارت به کارت', 'دریافت کننده'), 'انتقال وجه دریافتی', '#1ABC9C'),
    CategoryRule('income', ('بازگشت کارمزد', 'برگشتی'), 'بازگشت وجه', '#E67E22'),
)

# ============================================================
# FALLBACK RULES - برای تراکنش‌های بدون تطابق خاص
# ============================================================

FALLBACK_RULES = (
    CategoryRule('expense', (), 'متفرقه هزینه', '#95A5A6'),
    CategoryRule('income', (), 'متفرقه درآمد', '#95A5A6'),
)


def match_category(
    description: str,
    kind: str,
    existing_categories: List,
    user
) -> Tuple[Optional, bool]:
    """
    Match or auto-create a category based on description and kind.

    Returns:
        Tuple[category_object, was_created]
    """
    description = normalize_text(description)

    # First, try to match with existing categories (exact or keyword match)
    for category in existing_categories:
        cat_name = normalize_text(category.name)
        if cat_name and cat_name in description:
            return category, False

    # Then try rules for auto-creation
    rules = [r for r in CATEGORY_RULES if r.kind == kind]

    for rule in rules:
        if not rule.keywords:
            continue
        # Check if any keyword exists in description
        if any(normalize_text(keyword) in description for keyword in rule.keywords):
            # Check if category already exists for this user
            existing = next(
                (c for c in existing_categories if normalize_text(c.name) == normalize_text(rule.category_name)),
                None
            )
            if existing:
                return existing, False

            # Create new category
            from categories.models import Category
            new_category = Category.objects.create(
                user=user,
                name=rule.category_name,
                color=rule.category_color,
                is_active=True
            )
            return new_category, True

    # No match found - user will assign manually
    return None, False


def classify_transaction(description: str, kind: str, categories: List, user) -> Optional:
    """
    Legacy function - now uses match_category but returns only category.
    """
    category, _ = match_category(description, kind, categories, user)
    return category