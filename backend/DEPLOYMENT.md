# Deployment Guide — GitHub → Render (backend) → Vercel (frontend)

Follow this in order. Total time: ~20-30 minutes.

## 0. Recommended repo layout

```
fraud-detection-system/
├── fraud-backend/         # Module 1 + 3 + 4 (FastAPI)
│   ├── app/
│   ├── requirements.txt
│   ├── render.yaml
│   └── Dockerfile          (optional)
├── fraud-frontend/         # Module 2 (React)
│   ├── src/
│   ├── package.json
│   └── vercel.json
├── .github/workflows/ci.yml
├── .gitignore
└── README.md
```
You can also keep backend and frontend as two separate GitHub repos — either
works with Render/Vercel. This guide assumes the monorepo layout above; if
you split them, ignore the `rootDir` / `working-directory` path adjustments.

---

## 1. Push to GitHub

```bash
cd fraud-detection-system
git init
git add .
git commit -m "Initial commit — fraud early-warning system"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

If you get a "repo not found" error, create the empty repo on GitHub first
(github.com → New repository → do NOT initialize with a README, since you
already have one locally).

---

## 2. Deploy backend on Render

1. Go to [render.com](https://render.com) → sign in with GitHub.
2. **New → Blueprint** → select your repo → Render auto-detects `render.yaml`.
   - If your backend is in a subfolder (`fraud-backend/`), set **Root Directory**
     to `fraud-backend` in the service settings (or adjust `rootDir` in `render.yaml`).
3. Render will ask you to fill in the env vars marked `sync: false`:
   - `DATABASE_URL` — leave blank to use SQLite (fine for a hackathon demo,
     but data resets on redeploy), or connect the free Postgres instance
     Render provisions from `render.yaml` and paste its connection string.
   - `GEMINI_API_KEY` — paste your key, or leave blank (AI layer runs in
     offline fallback mode automatically — safe either way).
   - `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` — optional,
     leave blank if you don't need real email alerts for the demo.
4. Click **Apply** → Render builds and deploys. First build takes 3-5 min.
5. Once live, note your backend URL: `https://fraud-detection-backend.onrender.com`
6. Verify it's up: open `https://fraud-detection-backend.onrender.com/docs`
   — you should see the Swagger UI.
7. Run the seed script once, from Render's **Shell** tab (or locally against
   the same `DATABASE_URL`):
   ```bash
   python seed_data.py
   ```

**Free-tier note:** Render's free web services spin down after ~15 min of
inactivity and take ~30-50 seconds to wake on the next request. If demoing
live, open the backend URL a minute before judges arrive to "warm it up."

---

## 3. Deploy frontend on Vercel

1. Go to [vercel.com](https://vercel.com) → sign in with GitHub.
2. **Add New → Project** → import your repo.
3. If frontend is in a subfolder, set **Root Directory** to `fraud-frontend`.
4. Vercel auto-detects Vite from `vercel.json` / `package.json`.
5. Add environment variable in the Vercel dashboard (Project → Settings →
   Environment Variables):
   ```
   VITE_API_BASE_URL = https://fraud-detection-backend.onrender.com
   ```
6. Click **Deploy**. Takes ~1-2 min.
7. Your frontend is now live at `https://<project-name>.vercel.app`.

---

## 4. Connect them (CORS)

Go back to Render → your backend service → Environment → update:
```
CORS_ORIGINS = https://<project-name>.vercel.app
```
This should match the `CORS_ORIGINS` env var read in `app/main.py`'s CORS
middleware setup from Module 1. Redeploy the backend for it to take effect
(Render auto-redeploys on env var change).

---

## 5. Final checklist before demo

- [ ] Backend `/docs` loads and shows all endpoints (auth, customer, loan,
      transaction, fraud, AI, reports)
- [ ] `seed_data.py` has been run — demo customers exist
- [ ] Frontend login page loads and successfully logs in against the live backend
- [ ] Dashboard charts render with real seeded data
- [ ] AI Assistant chat widget responds (check both with and without
      `GEMINI_API_KEY` set — both should work, one says `"source": "offline"`)
- [ ] PDF download button works end-to-end
- [ ] Excel export button works end-to-end
- [ ] Backend warmed up (open the URL ~1 min before judges see it, free tier)

---

## Alternative: Railway instead of Render

If you prefer Railway over Render, the included `Dockerfile` works there
directly:
1. railway.app → New Project → Deploy from GitHub repo
2. Railway detects the `Dockerfile` automatically
3. Add the same environment variables listed in `render.yaml` under
   Project → Variables
4. Railway gives you a public URL immediately — use that as
   `VITE_API_BASE_URL` on the Vercel side.
