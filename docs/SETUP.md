# Getting started

Everything you need to go from the repo to a running application.
Work through this in order.

---

## 0. The stack (decided — do not revisit)

| Tier | Choice |
|---|---|
| Language | **Python 3.11+** |
| Web framework | **Flask** |
| Templates | **Jinja2** (ships with Flask) — HTML rendered on the server |
| Database | **PostgreSQL** on Neon (already created) |
| Driver | **psycopg 3** |
| Styling | Plain CSS, one shared stylesheet from the UI style guide |
| Hosting | Render (free tier, deploys from GitHub) |

**Why server-rendered Jinja rather than a separate JavaScript frontend:**
the registration page already written is plain HTML, Jinja renders plain
HTML, and this way there is one application to run and one to deploy
instead of two. There is no React, no Node, no npm anywhere in this
project. If you see a tutorial that starts with `npm install`, it is not
for us.

---

## 1. Install locally (everyone)

| Tool | Check it worked |
|---|---|
| [Python 3.11+](https://python.org) | `python3 --version` prints 3.11 or higher |
| [Git](https://git-scm.com) | `git --version` prints something |
| [VS Code](https://code.visualstudio.com) + the Python extension | opens |

---

## 2. Create the accounts (one person, then share access)

| Service | What for | Notes |
|---|---|---|
| [Neon](https://neon.tech) | PostgreSQL database | **Already done.** Get the connection string from whoever set it up |
| [Render](https://render.com) | Hosting | Free tier sleeps after inactivity — fine for a class project |
| [Resend](https://resend.com) | Verification and alert email (FR-2, FR-13) | Free tier is enough |

Invite all four team members. Share credentials through a password
manager, **never through the repo**.

---

## 3. Repository structure

```
campus-book-exchange/
├── README.md
├── .gitignore
├── .env.example            committed — the template
├── .env                    NOT committed — real secrets
├── requirements.txt        every package we use, with versions
├── wsgi.py                 entry point
├── docs/
│   ├── SETUP.md            this file
│   ├── SRS.pdf
│   ├── design-document.pdf
│   └── schema-diagram.png
├── db/
│   └── schema.sql          tables, constraints, seed data
├── app/
│   ├── __init__.py         create_app() — wires everything together
│   ├── db.py               the shared connection pool
│   ├── blueprints/         one file per feature area
│   │   ├── auth.py             FR-1, FR-2, FR-3
│   │   ├── listings.py         FR-4 to FR-7
│   │   ├── search.py           FR-8 to FR-10
│   │   ├── messages.py         FR-11
│   │   ├── watchlist.py        FR-12, FR-13
│   │   └── budget.py           FR-14 to FR-17
│   ├── services/
│   │   ├── email.py            Resend wrapper
│   │   └── isbn.py             Open Library wrapper  (Adapter pattern)
│   ├── templates/          one .html per Figma screen
│   │   ├── base.html           the shell every page extends
│   │   └── register.html
│   └── static/
│       └── css/style.css   all colours, from the UI style guide
└── tests/
```

**A blueprint is Flask's word for a group of related routes in one
file.** `app/blueprints/listings.py` holds every URL to do with
listings. That is the whole idea — it means four people can work at once
without editing the same file.

---

## 4. Set up the database (already done — here for the record)

The Neon database is created and `db/schema.sql` has been run against
it: 14 tables, 12 courses, 14 materials, 15 course-material links,
5 meetup locations.

If you ever need to reset it, paste `db/schema.sql` into the Neon SQL
editor **in chunks** and check the table count after each one.

> **Two things we learned the hard way.** Never re-run SQL from Neon's
> History panel — it stores a truncated copy and will silently create
> half the tables. And strip any column-alignment spacing before
> pasting, because it can arrive as non-breaking spaces and break the
> parse.

Verify at any time with:

```sql
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
```

You should get 14.

---

## 5. Clone and run (everyone)

```bash
git clone https://github.com/<owner>/campus-book-exchange.git
cd campus-book-exchange

python3 -m venv .venv            # a private copy of Python for this project
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then fill in the real values
                                 # get them from whoever set up the accounts

flask --app wsgi run --debug     # http://localhost:5000
```

`.venv` keeps this project's packages out of your system Python. It is
in `.gitignore` — never commit it. You need to run `source
.venv/bin/activate` in every new terminal.

Now visit **http://localhost:5000/api/health**. You should see:

```json
{"ok": true, "database": "connected", "courses": 12}
```

That one response proves all three tiers are talking to each other: the
browser reached Flask, Flask reached Neon, and Neon has the seed data.
**If it says `"ok": false`, the error message tells you what is wrong —
it is almost always `DATABASE_URL` in `.env`.**

Then visit **http://localhost:5000/register** to see the registration
page.

---

## 6. Environment variables

Copy `.env.example` to `.env` and fill it in. `.env` is in `.gitignore`
and must stay there.

A leaked key in a public repo gets scraped within minutes. If one is
committed by accident, rotate it immediately — deleting the commit is
not enough, because it stays in the history.

---

## 7. How to write a route

The pattern, so all four of us write it the same way:

```python
from flask import Blueprint, render_template
from app import db

bp = Blueprint("listings", __name__)

@bp.get("/listings/<int:listing_id>")
def listing_detail(listing_id):
    listing = db.query_one(
        "SELECT * FROM listings WHERE id = %s AND status = 'active'",
        (listing_id,),
    )
    if listing is None:
        return render_template("not_found.html"), 404
    return render_template("listing_detail.html", listing=listing)
```

Then register it once in `app/__init__.py`:

```python
from app.blueprints.listings import bp as listings_bp
app.register_blueprint(listings_bp)
```

**The one rule that matters:** always pass values as the second argument
to `query_one` / `query_all` / `execute`, using `%s` placeholders. Never
build the SQL string with an f-string. The driver escapes the values for
you with `%s`; it cannot protect you once you have glued the string
together yourself. That is how SQL injection happens.

---

## 8. Daily workflow

```bash
git checkout main
git pull                              # always start from current main
git checkout -b fr-1-registration     # branch named after the task ID

# ... work, committing as you go ...

git push -u origin fr-1-registration
```

Then open a pull request, request a review from one teammate, and merge
once approved.

**Rules the team agreed:**

- Never push directly to `main`.
- One branch per task, named after the task ID from the task breakdown.
- Push something every week even if it is incomplete. A branch that
  lives on one laptop for a month is a branch nobody can help with.
- If you install a package, add it to `requirements.txt` in the same PR.
  Otherwise it works on your laptop and nobody else's.
- Never commit `.env`, credentials, `.venv`, or `__pycache__`.

---

## 9. Build order

Work down this list. Each block depends on the one above it.

### Sprint 0 — foundation (all four, together)

- [x] Stack decided — Python + Flask
- [x] Database created and `db/schema.sql` run against it
- [x] Flask skeleton with `/api/health` returning `{"ok": true}`
- [ ] Deployed to Render, with `/api/health` green **in production**
- [ ] `base.html` shell and bottom navigation, with empty pages behind it
- [ ] Shared CSS finished from the style guide
- [ ] `pytest` installed with one passing example test
- [ ] Branch protection on `main` turned on in GitHub settings

**Nobody starts feature work until `/api/health` is green in
production.** Teams that skip this discover their deployment problems in
week 14.

### Sprint 1 — accounts

- [ ] FR-1 registration: route, server-side validation, bcrypt hashing
- [ ] FR-2 verification: token, email, verify route
- [ ] FR-2 **`@require_verified` decorator** — this blocks everyone else, do it early
- [ ] FR-3 login, logout, sessions

While that happens, everyone else builds their templates against fake
data passed straight into `render_template`. Do not wait for auth to
exist before writing pages.

### Sprint 2 — the marketplace loop

- [ ] FR-4, FR-5, FR-6 create a listing with photos and types
- [ ] FR-8 search
- [ ] FR-10 listing detail

At the end of this sprint one student can post a book and another can
find it. That is the minimum demonstrable product.

### Sprint 3 — completing the product

- [ ] FR-7 manage listings, **including the ownership test**
- [ ] FR-9 filter and sort
- [ ] FR-11 messaging
- [ ] FR-14 to FR-17 the budget planner

### Sprint 4 — second increment

- [ ] FR-12, FR-13 watchlist and alerts
- [ ] FR-18 meetup locations
- [ ] Remaining P2 tasks

### Sprint 5 — hardening (reserve this; schedule no new features)

- [ ] Integration testing across features
- [ ] Accessibility pass against the style guide checklist
- [ ] FR-19 / FR-20 review: confirm no form anywhere collects payment details
- [ ] Bug fixing, documentation, demo rehearsal

---

## 10. External services

### ISBN lookup (FR-5)

Open Library is free and needs no key:

```
https://openlibrary.org/api/books?bibkeys=ISBN:9781119594611&format=json&jscmd=data
```

Wrap it in `app/services/isbn.py` so the rest of the code sees our own
shape, not theirs. That wrapper **is** the Adapter pattern from the
reflection — if we later swap to Google Books, only that file changes.

Handle the lookup failing. A seller must still be able to type the title
by hand (FR-5 alternate flow).

### Email (FR-2, FR-13)

Resend's free tier is enough. Keep `EMAIL_DEV_LOG_ONLY=true` in your
local `.env` — verification links then print to your terminal instead of
being sent. You will register dozens of test accounts and you do not
want them all in an inbox.

### Course materials (FR-15)

Twelve courses are already seeded. **The retail prices in `schema.sql`
are placeholders.** Check them against the UNT bookstore before the
demo, or the budget planner will show numbers nobody can defend if
asked.

---

## 11. Definition of done

A task is finished only when all of these are true.

- [ ] Merged into `main`, not sitting on one laptop
- [ ] Works against the **deployed** site, not only localhost
- [ ] Validation enforced on the server, not only in the browser
- [ ] At least one test for the success path and one for a failure path
- [ ] Works on a phone-sized screen
- [ ] Reviewed by another team member
- [ ] Any new package added to `requirements.txt`

---

## 12. Three things that will bite you

**The verification check (FR-2) blocks listings, messaging, and the
watchlist.** It is the highest-risk item in the schedule. Build it in
Sprint 1 and tell everyone the moment it is merged.

**Server-side validation is not optional.** Every rule the browser
checks must be checked again in the route. A client-side check is for
the user's convenience; it is not security, because anyone can POST
straight to the URL with `curl` and never load the page at all.

**The ownership check on listings (FR-7) is the one security bug a
reviewer will actually try.** Before you call FR-7 done, write a test
that signs in as user A and attempts to delete user B's listing. It must
return 403.
