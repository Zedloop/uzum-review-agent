import requests

from config import Config

PAGE_SIZE = 50
MAX_PAGES = 20


class UzumClient:
    """Uzum seller boshqaruv paneli (seller.uzum.uz) ichki API'si bilan ishlash.

    Rasmiy ochiq Seller OpenAPI'da sharhlar bilan ishlash imkoniyati yo'q,
    shuning uchun boshqaruv paneli o'zi ishlatadigan ichki so'rovlar aniqlanib
    (brauzer DevTools orqali) ishlatilmoqda.
    """

    def __init__(self):
        self.base_url = Config.UZUM_API_BASE_URL.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {Config.UZUM_API_KEY}",
                "Content-Type": "application/json",
            }
        )

    def fetch_unanswered_reviews(self):
        allowed_shops = {str(shop_id) for shop_id in Config.UZUM_SHOP_IDS}
        collected = []

        for page in range(MAX_PAGES):
            url = f"{self.base_url}/product-reviews"
            response = self.session.post(
                url, params={"page": page, "size": PAGE_SIZE}, json={}
            )
            response.raise_for_status()
            items = response.json().get("payload", [])
            if not items:
                break

            for item in items:
                if item.get("replyStatus") is not None:
                    continue
                if str(item.get("shop", {}).get("id")) not in allowed_shops:
                    continue
                collected.append(item)

        collected.sort(key=lambda item: item["dateCreated"])
        return collected

    def send_reply(self, review_id, reply_text):
        url = f"{self.base_url}/product-reviews/reply/create"
        response = self.session.post(
            url, json=[{"reviewId": int(review_id), "content": reply_text}]
        )
        response.raise_for_status()
        return response.json()
