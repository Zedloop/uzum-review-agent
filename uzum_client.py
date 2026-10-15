import requests

from config import Config
from uzum_auth import fetch_new_token, get_valid_token

PAGE_SIZE = 50
MAX_PAGES = 20
EMPTY_PAGE_STOP_STREAK = 3


class UzumClient:
    """Uzum seller boshqaruv paneli (seller.uzum.uz) ichki API'si bilan ishlash.

    Rasmiy ochiq Seller OpenAPI'da sharhlar bilan ishlash imkoniyati yo'q,
    shuning uchun boshqaruv paneli o'zi ishlatadigan ichki so'rovlar aniqlanib
    (brauzer DevTools orqali) ishlatilmoqda.
    """

    def __init__(self):
        self.base_url = Config.UZUM_API_BASE_URL.rstrip("/")
        self.session = requests.Session()
        self._set_auth_header(get_valid_token())

    def _set_auth_header(self, token):
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
        )

    def _post(self, url, **kwargs):
        response = self.session.post(url, **kwargs)
        if response.status_code == 401 and Config.UZUM_USERNAME and Config.UZUM_PASSWORD:
            # Token muddati tugagan bo'lishi mumkin - login/parol orqali yangi
            # token olib, so'rovni bir marta qayta sinab ko'ramiz.
            self._set_auth_header(fetch_new_token())
            response = self.session.post(url, **kwargs)
        response.raise_for_status()
        return response

    def fetch_unanswered_reviews(self):
        allowed_shops = {str(shop_id) for shop_id in Config.UZUM_SHOP_IDS}
        collected = []
        empty_streak = 0

        # Uzum sharhlarni eng yangisidan boshlab qaytaradi, shuning uchun bir nechta
        # ketma-ket sahifada yangi javobsiz sharh topilmasa, qolgan (eskiroq) tarix
        # ham allaqachon javoblangan deb hisoblab, erta to'xtaymiz. Bu tez-tez
        # (masalan har 5 daqiqada) tekshirishda har safar butun tarixni qayta
        # skanerlab, Uzum'ni ortiqcha so'rovlar bilan band qilib qo'yishning oldini oladi.
        for page in range(MAX_PAGES):
            url = f"{self.base_url}/product-reviews"
            response = self._post(url, params={"page": page, "size": PAGE_SIZE}, json={})
            items = response.json().get("payload", [])
            if not items:
                break

            found_on_page = 0
            for item in items:
                if item.get("replyStatus") is not None:
                    continue
                if str(item.get("shop", {}).get("id")) not in allowed_shops:
                    continue
                collected.append(item)
                found_on_page += 1

            if found_on_page == 0:
                empty_streak += 1
                if empty_streak >= EMPTY_PAGE_STOP_STREAK:
                    break
            else:
                empty_streak = 0

        collected.sort(key=lambda item: item["dateCreated"])
        return collected

    def send_reply(self, review_id, reply_text):
        url = f"{self.base_url}/product-reviews/reply/create"
        response = self._post(url, json=[{"reviewId": int(review_id), "content": reply_text}])
        return response.json()
