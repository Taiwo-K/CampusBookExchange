"""
Messaging — FR-11.

Buyers and sellers talk about one listing at a time. The schema does most
of the work:

    CONSTRAINT conversations_unique    UNIQUE (listing_id, buyer_id)
    CONSTRAINT conversations_not_self  CHECK  (buyer_id <> seller_id)

One thread per buyer per listing, and nobody messages themselves. Both are
enforced in the database, so the routes below only have to turn them into
sentences instead of 500s.

Access control: every query is filtered by the signed-in user's id. A
conversation you are not part of does not come back from the database at
all, so there is nothing to leak — rather than fetching it and then
deciding whether to show it.
"""

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for
)

from app import db
from app.auth import current_user_id, require_verified

bp = Blueprint("messages", __name__)

MAX_BODY = 2000


# ---------------------------------------------------------------------
#  Inbox
# ---------------------------------------------------------------------

INBOX_SQL = """
    SELECT c.id,
           c.listing_id,
           l.title AS listing_title,
           l.status AS listing_status,
           u.first_name || ' ' || u.last_name AS other_name,
           (SELECT m.body FROM messages m
             WHERE m.conversation_id = c.id
             ORDER BY m.sent_at DESC LIMIT 1) AS last_body,
           (SELECT m.sent_at FROM messages m
             WHERE m.conversation_id = c.id
             ORDER BY m.sent_at DESC LIMIT 1) AS last_at,
           (SELECT COUNT(*) FROM messages m
             WHERE m.conversation_id = c.id
               AND m.sender_id <> %(me)s
               AND m.read_at IS NULL) AS unread
      FROM conversations c
      JOIN listings l ON l.id = c.listing_id
      JOIN users u
        ON u.id = CASE WHEN c.buyer_id = %(me)s
                       THEN c.seller_id ELSE c.buyer_id END
     WHERE c.buyer_id = %(me)s OR c.seller_id = %(me)s
     ORDER BY last_at DESC NULLS LAST
"""


@bp.get("/messages")
@require_verified
def inbox():
    rows = db.query_all(INBOX_SQL, {"me": current_user_id()})
    return render_template("messages.html", conversations=rows)


# ---------------------------------------------------------------------
#  One conversation
# ---------------------------------------------------------------------


@bp.get("/messages/<int:conversation_id>")
@require_verified
def thread(conversation_id):
    me = current_user_id()

    # The OR in the WHERE clause is the whole access check. Someone who is
    # neither the buyer nor the seller gets no row back, and therefore a
    # 404 — the same answer as a conversation that does not exist, so the
    # URL cannot be used to find out which ids are real.
    convo = db.query_one(
        """
        SELECT c.id, c.listing_id, c.buyer_id, c.seller_id,
               l.title AS listing_title,
               u.first_name || ' ' || u.last_name AS other_name
          FROM conversations c
          JOIN listings l ON l.id = c.listing_id
          JOIN users u
            ON u.id = CASE WHEN c.buyer_id = %(me)s
                           THEN c.seller_id ELSE c.buyer_id END
         WHERE c.id = %(cid)s
           AND (c.buyer_id = %(me)s OR c.seller_id = %(me)s)
        """,
        {"cid": conversation_id, "me": me},
    )
    if convo is None:
        abort(404)

    messages = db.query_all(
        """
        SELECT m.id, m.sender_id, m.body, m.sent_at
          FROM messages m
         WHERE m.conversation_id = %s
         ORDER BY m.sent_at
        """,
        (conversation_id,),
    )

    # Opening the thread marks the other person's messages as read. Only
    # theirs — your own are read by definition.
    db.execute(
        """
        UPDATE messages SET read_at = NOW()
         WHERE conversation_id = %s AND sender_id <> %s AND read_at IS NULL
        """,
        (conversation_id, me),
    )

    return render_template(
        "conversation.html", convo=convo, messages=messages, me=me
    )


@bp.post("/messages/<int:conversation_id>")
@require_verified
def send(conversation_id):
    me = current_user_id()
    body = request.form.get("body", "").strip()

    # Same membership check as above, before anything is written.
    member = db.query_one(
        """
        SELECT id FROM conversations
         WHERE id = %s AND (buyer_id = %s OR seller_id = %s)
        """,
        (conversation_id, me, me),
    )
    if member is None:
        abort(404)

    if not body:
        flash("Type a message first.", "error")
    elif len(body) > MAX_BODY:
        flash(f"Messages must be {MAX_BODY} characters or fewer.", "error")
    else:
        db.execute(
            """
            INSERT INTO messages (conversation_id, sender_id, body)
            VALUES (%s, %s, %s)
            """,
            (conversation_id, me, body),
        )

    return redirect(url_for("messages.thread", conversation_id=conversation_id))


# ---------------------------------------------------------------------
#  Starting a conversation from a listing
# ---------------------------------------------------------------------


@bp.post("/listings/<int:listing_id>/message")
@require_verified
def start(listing_id):
    me = current_user_id()

    listing = db.query_one(
        "SELECT id, seller_id, status FROM listings WHERE id = %s",
        (listing_id,),
    )
    if listing is None:
        abort(404)

    # conversations_not_self would reject this anyway; catching it here
    # gets the user a sentence instead of a 500.
    if listing["seller_id"] == me:
        flash("That's your own listing.", "error")
        return redirect(url_for("search.search"))

    if listing["status"] != "active":
        flash("That listing is no longer available.", "error")
        return redirect(url_for("search.search"))

    # UNIQUE (listing_id, buyer_id) means a second attempt must not create
    # a second thread. The DO UPDATE is a no-op write whose only job is to
    # make RETURNING give back the existing row's id.
    convo = db.execute(
        """
        INSERT INTO conversations (listing_id, buyer_id, seller_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (listing_id, buyer_id)
        DO UPDATE SET listing_id = EXCLUDED.listing_id
        RETURNING id
        """,
        (listing_id, me, listing["seller_id"]),
    )
    conversation_id = convo["id"]

    # The form may carry a first message. If it does, send it; if not, the
    # user just lands in an empty thread.
    body = request.form.get("body", "").strip()
    if body and len(body) <= MAX_BODY:
        db.execute(
            """
            INSERT INTO messages (conversation_id, sender_id, body)
            VALUES (%s, %s, %s)
            """,
            (conversation_id, me, body),
        )

    return redirect(url_for("messages.thread", conversation_id=conversation_id))
