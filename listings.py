from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db

bp = Blueprint("listings", __name__)

@bp.get("/create_listing")
def create_listing_form():
    return render_template("create_listing.html")

@bp.post("/create_listing")
def create_listing_submit():


    book_title = request.form.get("book_title", "").strip()
    author = request.form.get("author", "").strip()
    edition = request.form.get("edition", "").strip()
    isbn = request.form.get("isbn", "").strip()
    retail_price = request.form.get("retail_price", "").strip()
    asking_price = request.form.get("asking_price", "").strip()

    textbook_image = request.files.get("textbook_image")

    errors = []
    if not book_title:
        errors.append("a title is required")
    if not author:
        errors.append("an author name is required")
    if not edition:
        errors.append("an edition number is required")
    if not isbn:
        errors.append("an isbn number is required")
    if not retail_price:
        errors.append("please enter the books retail price")
    if not asking_price:
        errors.append("please enter the price you want for the textbook")
    if not textbook_image:
        errors.append("Please submit a picture of your textbook")

    
    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("create_listing.html", form=request.form), 400

    listing = db.execute(
        """
        INSERT INTO listings (title, author, edition, isbn, retail_price)
        VALUES(%s, %s, %s, %s. %s)
        RETURNING id
        """,
        (book_title,author, edition, isbn, retail_price),
    )

    listing_id = listing["id"]
