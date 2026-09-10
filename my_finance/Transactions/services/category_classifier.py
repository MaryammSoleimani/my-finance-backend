from categories.models import Category


CATEGORY_RULES = {

    "خوراک": [
        "رستوران",
        "کافه",
        "غذا",
        "سوپر",
        "فست",
        "کترینگ"
    ],

    "حمل و نقل": [
        "اسنپ",
        "تپسی",
        "تاکسی",
        "بنزین",
        "مترو",
        "اتوبوس"
    ],

    "خرید": [
        "دیجی",
        "فروشگاه",
        "مارکت",
        "خرید"
    ],

    "قبوض": [
        "برق",
        "آب",
        "گاز",
        "همراه",
        "ایرانسل"
    ],

    "سلامت": [
        "دارو",
        "پزشک",
        "درمان",
        "بیمارستان"
    ],

    "سرگرمی": [
        "سینما",
        "بازی",
        "فیلم"
    ],

    "درآمد": [
        "حقوق",
        "واریز",
        "دریافت",
        "پرداخت حقوق"
    ]
}



def classify_transaction(
        user,
        description,
        kind
):

    text = description.lower()


    # بررسی قوانین
    for category_name, keywords in CATEGORY_RULES.items():

        for keyword in keywords:

            if keyword in text:

                category = Category.objects.filter(
                    user=user,
                    name__icontains=category_name
                ).first()

                if category:
                    return category



    # اگر پیدا نشد
    if kind == "income":

        category = Category.objects.filter(
            user=user,
            name__icontains="درآمد"
        ).first()

    else:

        category = Category.objects.filter(
            user=user,
            name__icontains="سایر"
        ).first()



    return category