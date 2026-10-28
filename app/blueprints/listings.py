"""
Listings — FR-4, FR-5, FR-6.

A sale must have a price, a trade or giveaway must not.
"""

import os
import secrets

from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from app import db

from app.auth import current_user_id, require_verified

bp = Blueprint("listings", __name__)

CONDITIONS = ("like_new", "good", "fair")
LISTING_TYPES = ("sale", "trade", "giveaway")
ALLOWED_IMAGES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PHOTOS = 5


@bp.get("/create_listing")
@require_verified
def create_listing_form():

    courses = db.query_all(
        "SELECT id, course_number, title FROM courses ORDER BY course_number"
    )
    return render_template("create_listing.html", courses=courses, form={})


@bp.post("/create_listing")
@require_verified
def create_listing_submit():


    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    edition = request.form.get("edition", "").strip()
    isbn = request.form.get("isbn", "").strip()
    retail_price = request.form.get("retail_price", "").strip()
    asking_price = request.form.get("price", "").strip()

    
    condition = request.form.get("condition", "")
    listing_type = request.form.get("listing_type", "")
    description = request.form.get("description", "").strip()
    course_id = request.form.get("course_id", type=int)

    # FIXED: getlist, not get - the form allows up to 5 photos.
    textbook_images = [
        f for f in request.files.getlist("textbook_image") if f and f.filename
    ]

    errors = []
    if not title:
        errors.append("a title is required")
    if not author:
        errors.append("an author name is required")
    if not edition:
        errors.append("an edition number is required")
    if not isbn:
        errors.append("an isbn number is required")
    if not description:
        errors.append("a description is required")
    if not textbook_images:
        errors.append("Please submit a picture of your textbook")

    
    if condition not in CONDITIONS:
        errors.append("please choose a condition")
    if listing_type not in LISTING_TYPES:
        errors.append("please choose a type of listing")

    
    price = None
    if listing_type == "sale":
        try:
            price = round(float(asking_price), 2)
        except ValueError:
            price = None
        if price is None or price <= 0:
            errors.append("please enter the price you want for the textbook")
    elif asking_price:
        errors.append("free and trade listings can't have a price")

    
    retail = None
    if retail_price:
        try:
            retail = round(float(retail_price), 2)
        except ValueError:
            errors.append("the retail price has to be a number")

    if errors:
        for e in errors:
            flash(e, "error")
        # FIXED: courses has to be passed here too, or the dropdown is
        # empty when the form comes back with errors.
        courses = db.query_all(
            "SELECT id, course_number, title FROM courses ORDER BY course_number"
        )
        return render_template(
            "create_listing.html", courses=courses, form=request.form
        ), 400

    
    material = db.execute(
        """
        INSERT INTO materials (title, author, edition, isbn, retail_price)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (isbn) DO UPDATE SET isbn = EXCLUDED.isbn
        RETURNING id
        """,
        (title, author, edition, isbn, retail),
    )
    material_id = material["id"]

   
    listing = db.execute(
        """
        INSERT INTO listings
            (seller_id, material_id, course_id, title, isbn,
             price, condition, listing_type, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            current_user_id(), material_id, course_id or None, title, isbn,
            price, condition, listing_type, description,
        ),
    )
    listing_id = listing["id"]

    
    save_photos(listing_id, textbook_images)

    flash("Your listing is live.", "ok")
    return redirect(url_for("search.search", q=title))


def save_photos(listing_id, uploads):
    """FR-5 — save up to five photos and record them against the listing."""
    folder = os.path.join("app", "static", "uploads")
    os.makedirs(folder, exist_ok=True)

    for order, upload in enumerate(uploads[:MAX_PHOTOS]):
       
        ext = os.path.splitext(secure_filename(upload.filename))[1].lower()
        if ext not in ALLOWED_IMAGES:
            continue

        name = f"{secrets.token_hex(16)}{ext}"
        upload.save(os.path.join(folder, name))

        db.execute(
            """
            INSERT INTO listing_photos (listing_id, url, display_order)
            VALUES (%s, %s, %s)
            """,
            (listing_id, f"/static/uploads/{name}", order),
        )
