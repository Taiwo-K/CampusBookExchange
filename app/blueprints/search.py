"""
Search — FR-8.

One route. The query matches on title (partial, case-insensitive),
ISBN (exact) or course number (exact), and only ever returns listings
that are still active.
"""

from flask import Blueprint, render_template, request

from app import db

bp = Blueprint("search", __name__)

SEARCH_SQL = """
    SELECT l.id,
           l.title,
           l.price,
           l.condition,
           l.listing_type,
           c.course_number,
           (SELECT p.url
              FROM listing_photos p
             WHERE p.listing_id = l.id
             ORDER BY p.display_order
             LIMIT 1) AS photo_url
      FROM listings l
      LEFT JOIN courses c ON c.id = l.course_id
     WHERE l.status = 'active'
       AND (   l.title ILIKE %(pattern)s
            OR l.isbn = %(term)s
            OR UPPER(c.course_number) = UPPER(%(term)s)
           )
     ORDER BY l.created_at DESC
     LIMIT 50
"""


@bp.get("/search")
def search():
    term = request.args.get("q", "").strip()

    # An empty search returns nothing, not everything.
    
    if not term:
        return render_template("search.html", query="", results=None)

    results = db.query_all(
        SEARCH_SQL,
        {"pattern": f"%{term}%", "term": term},
    )
    return render_template("search.html", query=term, results=results)
