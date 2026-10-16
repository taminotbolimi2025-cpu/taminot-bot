# 📦 Ta'minot Bo'limi Vazifalar Boti (Telegram Task Bot)

Ta'minot bo'limi (ta'minotchi / ta'minot guruhi) xodimlari uchun topshiriqlarni tezkor taqsimlash va ularning bajarilishini umumiy guruhda shaffof nazorat qilish boti.

---

## 🚀 Imkoniyatlari

1. 👑 **Rahbar (Admin) uchun:**
   - Bot ichida **"➕ Yangi vazifa berish"** tugmasi orqali xodimni ro'yxatdan tanlash va vazifa matnini yuborish.
   - Vazifa darhol tanlangan xodimning shaxsiy Telegramiga boradi.
   - **"📋 Vazifalar nazorati"**: Faol (kutilmoqda/jarayonda) va bajarilgan vazifalarni real vaqt rejimida ko'rish.
   - **"👥 Xodimlar ro'yxati"**: Botga ulangan barcha ta'minotchilar ro'yxati.

2. 👷‍♂️ **Xodimlar (4-5 kishi) uchun:**
   - Shaxsiy xabarda yangi vazifa haqida xabarnoma.
   - Vazifa tagida 2 ta qulay tugma:
     - **⏳ Jarayonda** (ish boshlanganini bildirish)
     - **✅ Bajarildi** (bir marta bosish kifoya!)
   - **"📋 Mening vazifalarim"** menyusi orqali o'zining barcha faol topshiriqlarini ko'rish.

3. 📢 **Umumiy Telegram Guruhi uchun:**
   - Xodim **"✅ Bajarildi"** tugmasini bosishi bilan bot umumiy Ta'minot guruhiga darhol hisobot yuboradi:
     > **🎉 VAZIFA BAJARILDI!**  
     > 👤 **Xodim:** Ali Valiyev  
     > 📝 **Vazifa:** A-blok uchun 20 qop sement yetkazildi  
     > ⏱ **Bajarildi:** 16.10.2026 10:30  
     > ✅ *Ta'minot bo'limi nazorati ostida*

---

## ⚙️ O'rnatish va Ishga Tushirish

### 1-qadam: Bot Token va Admin ID olish
1. Telegramda [@BotFather](https://t.me/BotFather) botiga kiring va `/newbot` buyrug'i orqali yangi bot oching. Sizga berilgan **API Token**ni nusxalang.
2. O'zingizning Telegram ID raqamingizni bilish uchun Telegramda [@userinfobot](https://t.me/userinfobot) ga `/start` yozing va ID raqamingizni oling (masalan: `123456789`).

### 2-qadam: `.env` faylini to'ldirish
Loyiha papkasidagi `.env` faylini oching va ma'lumotlarni yozing:
```env
BOT_TOKEN=1234567890:AAH...sizning_tokeningiz
ADMIN_IDS=123456789
```
*(Agar adminlar bir nechta bo'lsa, vergul bilan yozing: `ADMIN_IDS=123456789,987654321`)*

### 3-qadam: Botni ishga tushirish
* Windows tizimida oddiygina **`start.bat`** faylini ikki marta bosing!
* Yoki buyruqlar satrida:
  ```bash
  .venv\Scripts\python.exe bot.py
  ```

---

## 👥 Guruhni Botga Ulash (1 daqiqalik ish)

1. Botni Ta'minot guruhingizga a'zo qiling.
2. Botga guruhda xabar yoza olishi uchun **Adminlik huquqini** bering.
3. Shu guruh ichida **`/set_group`** buyrug'ini yuboring.
4. Bot javob beradi: *«Guruh muvaffaqiyatli ulandi!»*.
5. Bo'ldi! Endi vazifalar bajarilganda barcha hisobotlar avtomatik shu guruhga tushadi.
