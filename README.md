# 🚗 Probka.uz — Telegram Bot

O'zbekiston yo'llaridagi tirbandlik, avariya va xavfli holatlar haqida tezkor xabar beruvchi bot.

---

## ⚙️ O'rnatish

### 1. Bot yaratish
1. Telegramda [@BotFather](https://t.me/BotFather) ga yozing
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting: `Probka Uz`
4. Username kiriting: `probka_uz_bot`
5. Olingan **TOKEN** ni saqlang

### 2. Kanal yaratish
1. Telegramda yangi kanal oching: `Probka.uz`
2. Username: `@probka_uz`
3. Botni kanalga **admin** qilib qo'shing (post yuborish huquqi bilan)

### 3. Admin ID olish
1. [@userinfobot](https://t.me/userinfobot) ga yozing
2. U sizning Telegram ID ngizni ko'rsatadi

### 4. .env fayl yaratish
```bash
cp .env.example .env
```
`.env` faylini oching va quyidagilarni to'ldiring:
```
BOT_TOKEN=your_token_here
CHANNEL_ID=@probka_uz
ADMIN_IDS=your_telegram_id
```

---

## 🚀 Railway da deploy qilish (BEPUL)

### 1. GitHub ga yuklash
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/username/probka-bot.git
git push -u origin main
```

### 2. Railway.app
1. [railway.app](https://railway.app) ga kiring
2. **New Project** → **Deploy from GitHub repo**
3. Reponi tanlang
4. **Variables** bo'limiga o'ting va `.env` dagi o'zgaruvchilarni qo'shing:
   - `BOT_TOKEN`
   - `CHANNEL_ID`
   - `ADMIN_IDS`
5. Deploy tugmachasini bosing ✅

---

## 🎮 Bot ishlash tartibi

```
Foydalanuvchi → Xabar turini tanlaydi
             → Matn yozadi
             → (ixtiyoriy) Lokatsiya yuboradi
             → Admin ga boradi (moderatsiya)
             → Admin tasdiqlaydi → Kanalga joylashadi
```

---

## 📁 Fayl tuzilmasi

```
probka_bot/
├── bot.py          # Asosiy bot kodi
├── requirements.txt # Kutubxonalar
├── .env.example    # O'zgaruvchilar namunasi
├── .env            # O'zgaruvchilar (git ga yuklanmaydi!)
└── README.md       # Yo'riqnoma
```

---

## 🔮 Kelajakdagi imkoniyatlar

- [ ] Yandex.Maps API orqali avtomatik tirbandlik ma'lumotlari
- [ ] Shahar bo'yicha filtrlash (Toshkent, Samarqand, Buxoro...)
- [ ] Statistika paneli
- [ ] Reklama tizimi
- [ ] Premium obuna

---

## 📞 Muammo bo'lsa

Telegram: @your_username
