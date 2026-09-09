"""Category matching utilities for imported bank transactions.

The importer must only select from the user's active categories.  Rules below
therefore describe *aliases* for category names rather than categories to
create.  The order is significant: merchant-specific rules are evaluated
before generic bank-statement wording.
"""

from dataclasses import dataclass


_CHARACTER_TRANSLATION = str.maketrans({
    'ي': 'ی',
    'ى': 'ی',
    'ك': 'ک',
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
})


def normalize_text(value):
    """Normalize Persian/Arabic spelling, digits, whitespace and case."""
    return ' '.join(str(value or '').translate(_CHARACTER_TRANSLATION).casefold().split())


@dataclass(frozen=True)
class CategoryRule:
    kind: str
    description_terms: tuple[str, ...]
    category_aliases: tuple[str, ...]


# Keep merchant rules ahead of broad descriptions such as "خرید کالا و خدمات".
CATEGORY_RULES = (
    CategoryRule('expense', ('اسنپ', 'تپسی'), ('حمل و نقل', 'رفت و آمد', 'transport')),
    CategoryRule('expense', ('دیجی کالا', 'دیجیکالا'), ('خرید', 'کالا', 'shopping')),
    CategoryRule('expense', ('کافه بازار', 'مایکت'), ('نرم افزار', 'اشتراک', 'software')),
    CategoryRule('expense', ('خرید کالا و خدمات', 'خرید'), ('خرید', 'کالا', 'shopping')),
    CategoryRule('expense', ('قبض', 'آب و فاضلاب', 'برق', 'گاز'), ('قبوض', 'utilities')),
    CategoryRule('expense', ('داروخانه', 'بیمارستان', 'درمان'), ('درمان', 'سلامت', 'health')),
    CategoryRule('income', ('حقوق', 'دستمزد'), ('حقوق', 'درآمد', 'salary', 'income')),
    CategoryRule('income', ('سود سپرده', 'سود'), ('سود', 'درآمد', 'income')),
)


def _category_for_aliases(categories, aliases):
    normalized_aliases = [normalize_text(alias) for alias in aliases]
    for category in categories:
        name = normalize_text(category.name)
        if any(alias == name or alias in name or name in alias for alias in normalized_aliases):
            return category
    return None


def classify_transaction(description, kind, categories):
    """Return an active user category matching ``description`` and ``kind``.

    ``categories`` must already be scoped to the importing user and active
    categories.  ``None`` is deliberately returned when no rule matches.
    """
    description = normalize_text(description)
    categories = list(categories)

    for rule in CATEGORY_RULES:
        if rule.kind != kind:
            continue
        if any(normalize_text(term) in description for term in rule.description_terms):
            category = _category_for_aliases(categories, rule.category_aliases)
            if category:
                return category

    # A user may name a category after a merchant or a phrase in its statement.
    # This fallback remains deterministic and never invents a category.
    for category in categories:
        name = normalize_text(category.name)
        if name and name in description:
            return category

    return None
