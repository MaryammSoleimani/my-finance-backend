import google.generativeai as genai
from django.conf import settings


class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        # تغییر به نسخه Flash برای سرعت بیشتر
        self.model = genai.GenerativeModel(
            'gemini-3.6-flash',  # به جای gemini-3.6-flash (این مدل وجود نداره!)
            system_instruction=self._get_system_instruction()
        )
        # کش کردن دیتا در حافظه برای استفاده مجدد
        #self.user_data = None
        #self.is_first_message = True

    def _get_system_instruction(self):
        return """
        You are a smart financial assistant. 

        RULES:
        1. ONLY use financial data if the user's question is DIRECTLY about numbers, money, expenses, income, or house buying.
        2. If user says "hi", "hello", or just greets, ONLY reply with a short greeting like "Hello! How can I help you today?" - NO DATA.
        3. Keep responses SHORT (max 5 sentences or 4 bullet points with emojis).
        4. ALWAYS use proper paragraph breaks and formatting. Use short titles like 📊 Summary or ✅ Action Items.
        5. Speak like a real advisor, NOT like an accountant.
        6. If user asks about buying a house, give a brief realistic answer without lengthy explanations.
        """

    def get_response(self, user_message, user_data):

        # ذخیره دیتا برای استفاده مجدد
        #self.user_data = user_data

        # تشخیص اینکه آیا سوال نیاز به دیتا داره یا نه
        needs_data = self._needs_financial_data(user_message)

        # ساخت پیام بر اساس نیاز
        if needs_data and self.user_data:
            message = self._build_message_with_data(user_message)
        else:
            message = user_message  # فقط پیام کاربر رو بفرست

        # ارسال به مدل
        response = self.model.generate_content(message)
        return response.text

    def _needs_financial_data(self, message):

        keywords = ['money', 'income', 'expense', 'debt', 'liability',
                    'asset', 'net worth', 'buy house', 'house', 'home',
                    'budget', 'spend', 'save', 'loan', 'mortgage',
                    'پول', 'درآمد', 'خرج', 'بدهی', 'دارایی', 'خانه']

        message_lower = message.lower()
        return any(keyword in message_lower for keyword in keywords)

    def _build_message_with_data(self, user_message):

        data_text = f"""
        User's Financial Data (ONLY use if relevant):
        - Total Assets: ${self.user_data.get('total_assets', 0)}
        - Total Liabilities: ${self.user_data.get('total_liabilities', 0)}
        - Net Worth: ${self.user_data.get('net_worth', 0)}
        - Monthly Income: ${self.user_data.get('monthly_income', 0)}
        - Monthly Expenses: ${self.user_data.get('monthly_expenses', 0)}
        """

        return f"{data_text}\n\nUser Question: {user_message}"