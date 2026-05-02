# 🚀 دليل Deploy — MedPrep Elite

## الخطة الكاملة
- **Backend (FastAPI)** → Render
- **Frontend (React)** → Vercel  
- **Database (MongoDB)** → MongoDB Atlas (مجاني)

---

## الخطوة 1 — MongoDB Atlas (قاعدة البيانات)

1. روح على https://cloud.mongodb.com وافتح حساب مجاني
2. اعمل **New Project** → اسمه `medprep`
3. اعمل **Create Cluster** → اختار M0 Free
4. من **Database Access**: اعمل user جديد وخد الـ username/password
5. من **Network Access**: اضغط **Add IP Address** → اختار **Allow Access from Anywhere** (0.0.0.0/0)
6. من **Connect** → **Drivers** → انسخ الـ connection string:
   ```
   mongodb+srv://USERNAME:PASSWORD@cluster0.xxxxx.mongodb.net/medprep_prod
   ```
   ⚠️ استبدل USERNAME وPASSWORD بالبيانات اللي اخترتها

---

## الخطوة 2 — Backend على Render

1. روح على https://render.com وسجل دخول
2. اضغط **New** → **Web Service**
3. وصّل GitHub repo بتاعك (أو ارفع الكود)
4. الإعدادات:
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. من **Environment Variables** أضف:

   | Key | Value |
   |-----|-------|
   | `MONGO_URL` | connection string من Atlas |
   | `DB_NAME` | `medprep_prod` |
   | `JWT_SECRET` | أي كلمة سر طويلة عشوائية |
   | `CORS_ORIGINS` | `*` (مؤقتاً، هتغيره بعدين) |
   | `OPENROUTER_API_KEY` | مفتاحك |
   | `STRIPE_API_KEY` | مفتاحك |
   | `TELEGRAM_BOT_TOKEN` | مفتاحك |
   | `ENABLE_ADVANCED_FEATURES` | `false` |
   | `HF_HOME` | `/tmp/hf_cache` |

6. اضغط **Create Web Service**
7. استنّى 5-10 دقايق للـ build
8. انسخ الـ URL جه زي: `https://medprep-backend.onrender.com`

### ✅ تأكد إن البكند شغال:
افتح في المتصفح: `https://medprep-backend.onrender.com/api/health`  
المفروض ترجع `{"status": "ok"}`

---

## الخطوة 3 — Frontend على Vercel

1. في مجلد `frontend`، افتح ملف `.env` وغير:
   ```
   REACT_APP_BACKEND_URL=https://medprep-backend.onrender.com
   REACT_APP_ADVANCED=false
   ```

2. روح على https://vercel.com وسجل دخول
3. اضغط **New Project** → **Import** من GitHub
4. اختار folder الـ `frontend` كـ Root Directory
5. Vercel هيكتشف إنه Create React App تلقائياً
6. ضيف Environment Variable:
   - `REACT_APP_BACKEND_URL` = `https://medprep-backend.onrender.com`
7. اضغط **Deploy**
8. بعد الـ deploy انسخ الـ URL زي: `https://medprep-elite.vercel.app`

---

## الخطوة 4 — ربط الـ CORS

بعد ما عندك Vercel URL، ارجع لـ Render وغير:
- `CORS_ORIGINS` = `https://medprep-elite.vercel.app`

(ده أهم لحماية الـ API)

---

## ⚠️ ملاحظات مهمة

### الـ BGE-M3 (RAG) والـ DICOM
- دول بياخدوا **أكثر من 2GB RAM** و**GPU**
- Render Free Plan مش هيكفي — محتاج على الأقل **Render Standard ($25/شهر)** أو **Render Pro**
- عشان كده `ENABLE_ADVANCED_FEATURES=false` للأول
- لما تجهّز plan مدفوع غيّره لـ `true`

### الـ ChromaDB والـ BGE-M3 Storage
- لازم تضيف persistent disk على Render
- أو استخدم **Chroma Cloud** بدل local

### Free Tier Limitations
- Render Free: السيرفر بيـ"ينام" بعد 15 دقيقة بدون requests
- MongoDB Atlas M0: 512MB storage مجاناً
- Vercel: مجاني للـ frontend تماماً

---

## الملفات المطلوب تضيفها للـ repo

| الملف | المكان | الغرض |
|-------|--------|--------|
| `render.yaml` | root | إعدادات Render تلقائية |
| `vercel.json` | `frontend/` | routing للـ React SPA |
| `Dockerfile` | `backend/` | لو حبيت Docker على Render |

---

## ترتيب الخطوات باختصار

```
1. MongoDB Atlas → انسخ connection string
2. Render → deploy backend + ضيف env vars
3. تأكد /api/health شغال
4. Vercel → deploy frontend مع BACKEND_URL
5. Render → حدّث CORS_ORIGINS بـ Vercel URL
6. افتح الموقع وجرّب Login ✅
```
