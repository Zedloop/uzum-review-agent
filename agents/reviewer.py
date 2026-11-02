import json

from agents._llm import generate_text
from config import Config

SYSTEM_PROMPT = """Siz Uzum Market do'koni javoblarini tekshiruvchi muharrirsiz.
Berilgan mijoz sharhi va unga yozilgan javobni baholang: u professional,
xushmuomala, aniq va sharh mazmuniga mos bo'lishi kerak, VA javob mijoz sharhi
yozilgan til bilan bir xil tilda bo'lishi shart (masalan, sharh ruscha bo'lsa,
javob ham ruscha bo'lishi kerak - aks holda rad eting).
Shuningdek, javob umumiy andozaviy jumlalardan (masalan hech narsaga ishora
qilmaydigan "uzr so'raymiz, sifat biz uchun muhim" kabi bo'sh iboralardan) emas,
balki sharhda aytilgan aniq narsaga (mahsulot, muammo, yoqqan/yoqmagan tomon)
ishora qilib yozilganini tekshiring - agar javob juda umumiy va shaxsiylashtirilmagan
bo'lsa, rad eting.
ENG MUHIMI: javobni imlo va grammatika xatolariga juda diqqat bilan tekshiring - noto'g'ri
yozilgan so'zlar, notog'ri qo'shimchalar, o'ylab topilgan/mavjud bo'lmagan so'zlar yoki
ma'nosiz/tushunarsiz jumlalar bo'lsa, albatta rad eting va feedback'da aniq qaysi so'z/jumla
xato ekanini ko'rsating. Javob xuddi ona tilida so'zlashuvchi savodli odam yozgandek,
tabiiy va toza bo'lishi shart.
Alohida mantiqiy xatoni ham tekshiring: javobda "...haqida yozganingiz/aytganingiz uchun
uzr so'raymiz" kabi noto'g'ri qurilma bo'lmasligi kerak (bu mijoz shikoyat yozgani uchun
uzr so'raganday eshitiladi) - uzr muammoning o'ziga bildirilishi kerak, mijoz uni
yozganiga emas. Shunday xato topsangiz, rad eting.
Faqat quyidagi JSON formatida javob bering, boshqa hech narsa yozmang:
{"approved": true yoki false, "feedback": "approved false bo'lsa, nima uchun va qanday tuzatish kerakligi"}"""


def review_reply(review_text, rating, draft_reply):
    prompt = (
        f'Mijoz sharhi (baho: {rating}/5):\n"{review_text}"\n\n'
        f'Yozilgan javob:\n"{draft_reply}"\n\n'
        "Ushbu javobni baholang."
    )

    text = generate_text(prompt, SYSTEM_PROMPT, Config.CLAUDE_MODEL_REVIEWER, json_mode=True)
    return json.loads(text)
