# 🚀 Deploy StorePilot AI — Panduan Lengkap

## Arsitektur

```
Frontend (Vercel) ──▶ Backend (Railway) ──▶ Database (Supabase)
```

---

## 1️⃣ Database — Supabase (Udah dipake)

Di **Supabase Dashboard → Project Settings → Database → Connection string**:

```
postgresql://postgres:[PASSWORD]@[PROJECT].supabase.co:5432/postgres?sslmode=require
```

Simpan untuk nanti.

---

## 2️⃣ Backend — Railway (Gratis)

### Step-by-step:

```bash
# 1. Push project ke GitHub
git add .
git commit -m "feat: ready for production deploy"
git push origin main

# 2. Buka https://railway.com
#    - Login pake GitHub
#    - New Project → Deploy from GitHub → pilih storepilot-ai

# 3. Set Environment Variables:
#    DATABASE_URL=postgresql://postgres:[PASSWORD]@[PROJECT].supabase.co:5432/postgres?sslmode=require
#    SECRET_KEY=<generate random: python -c "import secrets; print(secrets.token_urlsafe(32))">
#    CORS_ORIGINS=http://localhost:5500,https://storepilot.vercel.app
#    APP_ENV=production
#    DEBUG=false
#    AI_PROVIDER=fallback
#    ACCESS_TOKEN_EXPIRE_MINUTES=60

# 4. Railway auto-build & deploy
#    Dapetin URL: https://storepilot-api.up.railway.app
```

### Test backend:

```bash
curl https://storepilot-api.up.railway.app/api/health
# → {"status":"healthy","service":"StorePilot AI"}
```

---

## 3️⃣ Frontend — Vercel (Gratis)

### Step-by-step:

```bash
# 1. Buka https://vercel.com
#    - Login pake GitHub
#    - Add New Project → Import GitHub repo → storepilot-ai

# 2. SETTINGS PENTING:
#    Root Directory: StorePilot AI/
#    Build Command: (kosongin — static)
#    Output Directory: (kosongin)
#    Install Command: (kosongin)

# 3. Deploy → dapetin URL: https://storepilot.vercel.app
```

### Atau via CLI:

```bash
npm i -g vercel
cd "StorePilot AI"
vercel --prod
```

### Set URL Backend di Frontend:

Buka **Vercel Dashboard → Project → Settings → Environment Variables**:

| Variable | Value |
|----------|-------|
| `__API_BASE__` | `https://storepilot-api.up.railway.app` |

---

## 4️⃣ Final Ceklist

| ✅ | Item |
|---|------|
| ✅ | `StorePilot AI/js/api.js` — auto-detect backend URL (local vs production) |
| ✅ | `Procfile` — untuk Railway / Render |
| ✅ | `.env.example` — template environment variables |
| ✅ | Supabase connection string siap |
| ✅ | CORS_ORIGINS updated |
| ✅ | `start.sh` — auto migrate + seed |

---

## 5️⃣ Update CORS di Backend

Pastiin di environment variable Railway:

```
CORS_ORIGINS=http://localhost:5500,https://storepilot.vercel.app,https://storepilot.netlify.app
```

Atau di `app/main.py` biarkan wildcard `*` saat development, ganti ke list spesifik pas production.

---

## 6️⃣ Seed Database di Production

Jalanin seed satu kali via Railway:

```bash
# Buka Railway Dashboard → Project → Connect → Shell
python scripts/seed.py
```

Atau create tabel dulu:

```bash
# Dari Railway shell
python -c "
from app.core.database import Base, engine
from app import models_registry
Base.metadata.create_all(bind=engine)
print('✅ Tables created!')
"
python scripts/seed.py
```

---

## 7️⃣ Quick URLs

| Service | URL |
|---------|-----|
| Frontend (Vercel) | `https://storepilot.vercel.app` |
| Backend (Railway) | `https://storepilot-api.up.railway.app` |
| Swagger Docs | `https://storepilot-api.up.railway.app/docs` |
| Supabase Dashboard | `https://supabase.com/dashboard/project/[ID]` |

---

## 8️⃣ Troubleshooting

### "CORS error" di browser
→ Pastiin `CORS_ORIGINS` di Railway udah include URL frontend.

### "Database connection refused"
→ Cek Supabase → **Project Settings → Network → IP restrictions** — matiin atau allow Railway IP.

### "404 Not Found" di frontend
→ Cek `baseUrl` di `api.js` → pake URL Railway, bukan localhost.

### "Streaming response failed"
→ Global exception handler error. Cek Railway logs.

---

## 9️⃣ Biaya (Gratis)

| Service | Biaya |
|---------|-------|
| Supabase | **Free** (500MB database) |
| Railway | **Free** ($5 credit gratis/bulan) |
| Vercel | **Free** (100GB bandwidth) |
| **Total** | **$0/bulan** |

