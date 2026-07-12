# Sentinel — Fraud Detection Frontend

React (Vite) dashboard for the Bank Fraud Detection & Early Warning System.

## Tech Stack
- React 18 + Vite
- Tailwind CSS (custom "risk control room" design system)
- React Router v6
- Recharts (pie / bar / line charts)
- Axios (with JWT interceptor)
- lucide-react (icons), react-hot-toast (notifications)

## Folder Structure
```
fraud-frontend/
├── src/
│   ├── api/              # axios calls per backend module (auth, customer, loan, transaction, fraud)
│   ├── components/        # Sidebar, Topbar, RiskGauge, RiskBadge, AIAssistantPanel, Modal, etc.
│   ├── context/            # AuthContext (JWT session state)
│   ├── pages/
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx        # KPIs, fraud pie chart, branch-wise bar chart, live alerts
│   │   ├── Customers.jsx        # list + create
│   │   ├── CustomerDetail.jsx   # Risk Gauge, trend chart, triggered rules, AI explanation, AI assistant
│   │   ├── Alerts.jsx
│   │   └── Reports.jsx          # PDF / Excel export
│   ├── App.jsx
│   └── main.jsx
├── index.html
├── tailwind.config.js
└── package.json
```

## Setup

```bash
cd fraud-frontend
npm install
cp .env.example .env      # set VITE_API_URL if backend isn't on localhost:8000
npm run dev
```

Opens at **http://localhost:5173**. Make sure the backend is running at the URL in `.env`
and you've run `python seed_data.py` in the backend so there's demo data to explore.

Login with: **officer@bank.com / Officer@123**

## Features implemented
- JWT login/session (auto-redirect to `/login` on 401 / token expiry)
- Dashboard: KPI cards, fraud distribution pie chart, branch-wise risk bar chart, live alert feed
- Customers: searchable list, create customer modal
- Customer detail:
  - 🟢 Risk Gauge Meter (custom SVG instrument dial)
  - 📈 Risk trend line chart (score history over time)
  - Triggered rule breakdown with point contributions
  - AI-generated plain-English explanation
  - ⭐ Recommended actions checklist
  - 🤖 AI Assistant chat ("Why is this customer high risk?")
  - Add loan / add transaction forms
  - 📄 One-click PDF report download
- Alerts page with severity filters and mark-as-read
- Reports page with per-customer PDF + portfolio-wide Excel export

## Deployment (Vercel)
1. Push this folder to GitHub.
2. On Vercel: New Project → import repo → framework preset "Vite".
3. Add env var `VITE_API_URL` = your deployed Render backend URL.
4. Deploy.
