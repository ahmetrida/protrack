<div align="center">

# 🎓 ProTrack: Web-Based Academic Project Portal
### Enterprise Academic Project & Viva Voce Governance Platform

[![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/CSS)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.2%2B-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-TF--IDF%20AI-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)](https://scikit-learn.org)
[![UI Design](https://img.shields.io/badge/UI-Google%20Material%203-5E35B1?style=for-the-badge&logo=materialdesign&logoColor=white)](https://m3.material.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-137333?style=for-the-badge)](LICENSE)

**A role-verified, multi-tenant cloud workspace for Universities, Colleges, and Departments to manage academic project lifecycles, AI-powered abstract originality checks, weekly mentor sign-offs, and 100-point Viva Voce evaluations.**

[Live Demo](https://protrack.pythonanywhere.com) • [Report Bug](../../issues) • [Request Feature](../../issues)

</div>

---

## ✨ Key Architectural Features

### 🔐 1. Role-Gated Onboarding & Institutional Hierarchy
* **Descending Institutional Engine:** Strictly structured around `University ➔ College ➔ Department`.
* **Verified Institution Admins:** Admins upload mandatory **Front & Back Official ID Proofs** to register institutional entities, audit student and faculty datasets, and promote Faculty Guides to External Examiners.
* **Isolated Root Superadmin:** Complete backend and frontend isolation via `/superadmin-access/` and `/superadmin-console/`, ensuring root governance is never exposed in regular directories or role dropdowns.

### 🧠 2. Hybrid Scikit-Learn TF-IDF Originality Engine
* Real-time mathematical comparison of student project proposals against historical department archives and peer submissions.
* Combines **Word N-Gram TF-IDF**, **Character N-Gram TF-IDF**, and **Jaccard Token Overlap** with automated risk classification (`LOW`, `MODERATE`, `HIGH`).

### 👥 3. Smart Student Group Management
* **Interactive Classmate Search:** Real-time departmental student lookup by first name or roll call number.
* **5-Character Alphanumeric Join Codes:** Collision-safe, backend-validated group join codes (e.g., `A8K2P`) allowing unregistered teammates to join seamlessly after sign-up.
* **Weekly Progress Logbook:** Structured milestone tracking with Faculty Guide verification and feedback sign-offs.

### 📊 4. Examiner & HOD Analytics Portal
* **4-Pillar 100-Point Viva Rubric:** Live grading across *Problem Clarity (25)*, *Implementation (25)*, *Presentation & Defense (25)*, and *Documentation (25)* with automatic letter-grade badge computation (`O`, `A+`, `A`, `B+`, `B`).
* **Department KPIs & Visual Analytics:** Interactive Chart.js proposal distribution charts, TF-IDF corpus management, and 1-click **Master Gradebook CSV Export**.

### 💾 5. Google Material 3 UX, Audio Feedback & Auto-Save Persistence
* **Automatic Draft Persistence:** Dual-layer form auto-saving (`localStorage` + authenticated `/api/sync-drafts/` cloud sync) with live status indicators (`Saving...`, `Saved`) prevents data loss on accidental tab closures or refreshes.
* **Interactive Audio Feedback:** Plays celebratory confirmation audio (`Success.mp3`) on successful submissions and interactive validation audio prompts when required identity fields are skipped.
* **Role-Scoped Contact & WhatsApp Directory:** Clickable `wa.me` direct chat links, `mailto:`, `tel:`, GitHub, YouTube, and Instagram portfolio badges strictly filtered by each user's institutional authorization scope.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend Framework** | Python 3, Django 4.2+ |
| **AI / NLP Engine** | Scikit-Learn (`TfidfVectorizer`, `cosine_similarity`), Pandas, Pillow |
| **Database** | SQLite3 (Development) / PostgreSQL-Ready (Production) |
| **Frontend & Design System** | HTML5, CSS3 (Royal-Violet Google Material 3), Bootstrap 5.3, JavaScript (ES6+) |
| **Typography & Icons** | Google Sans, Plus Jakarta Sans, Lucide Vector Icons, Chart.js |

---

## 📂 Project Structure

* `build_protrack.py` — Master non-destructive builder and migration runner
* `manage.py` — Django CLI management utility
* `protrack_config/` — Core settings, URL routing, and WSGI configuration
* `portal/` — Models, hybrid TF-IDF similarity engine (`similarity.py`), role-scoped views, and APIs
* `templates/` — Responsive Google Material 3 HTML templates across all role dashboards
* `media/` — User avatars, project synopsis reports, admin ID proofs, and UI audio assets

---

## 🚀 Quickstart & Installation

### Option A: Local / GitHub Codespaces Setup

1. **Clone the repository:**
   `git clone https://github.com/ahmetrida/protrack.git && cd protrack`

2. **Install dependencies:**
   `pip install -r requirements.txt`

3. **Build application files and run migrations:**
   `python build_protrack.py`

4. **Start the development server:**
   `python manage.py runserver 0.0.0.0:8000`

### Option B: PythonAnywhere Cloud Deployment

1. **Sync with GitHub in the PythonAnywhere Bash console:**
   `cd ~/protrack && git fetch origin && git reset --hard origin/main`

2. **Activate virtual environment and run the builder:**
   `workon venv && python build_protrack.py`

3. **Reload Web App:**
   Open the PythonAnywhere **Web** tab and click **Reload protrack.pythonanywhere.com**.

---

## 🧭 Role Navigation & Access Routes

| Role | Access Route | Primary Responsibilities |
| :--- | :--- | :--- |
| **Student** | `/student/` | Create/join groups via 5-char code, scan abstract similarity, upload reports, log weekly tasks. |
| **Faculty Guide** | `/guide/` | Claim/mentor groups, approve or request changes on proposals, verify weekly logs. |
| **Examiner / HOD** | `/examiner/` | View department KPIs, manage TF-IDF archive corpus, grade 100-point Viva rubrics, export CSV. |
| **Institution Admin** | `/admin-portal/` | Promote/demote Examiners, audit college datasets, manage University ➔ College ➔ Department tree. |
| **Public Profile** | `/profile/<username>/` | Role-scoped public profile view with clickable email, phone, WhatsApp, and social links. |
| **Superadmin** | `/superadmin-access/` | Strictly isolated cross-university root console and global user management. |

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<div align="center">

**ProTrack Portal · Built by Ahmet Rida**  
*Google Material 3 • Scikit-Learn TF-IDF • Lucide Vector UI*

</div>
