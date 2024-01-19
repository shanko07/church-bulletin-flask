import io

from flask import Blueprint, send_file
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from .auth import login_required
from .db import get_db

bp = Blueprint("files", __name__)


@bp.route("/")
@login_required
def index():
    """Show all the files I own on here, most recent first."""
    db = get_db()

    files = db.execute(
        "SELECT f.id, f.friendly_title, f.contents, f.created, f.author_id, u.username"
        " FROM file f JOIN user u ON f.author_id = u.id"
        " WHERE u.id = ?"
        " ORDER BY created DESC",
        (g.user["id"],)
    ).fetchall()

    return render_template("files/index.html", files=files)


def get_file(id, check_author=True):
    """Get a post and its author by id.

    Checks that the id exists and optionally that the current user is
    the author.

    :param id: id of post to get
    :param check_author: require the current user to be the author
    :return: the post with author information
    :raise 404: if a post with the given id doesn't exist
    :raise 403: if the current user isn't the author
    """
    file = (
        get_db()
        .execute(
            "SELECT f.id, f.author_id, f.friendly_title"
            " FROM file f JOIN user u ON f.author_id = u.id"
            " WHERE f.id = ?",
            (id,),
        )
        .fetchone()
    )

    if file is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and file["author_id"] != g.user["id"]:
        abort(403)

    return file


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new post for the current user."""
    if request.method == "POST":
        title = request.form["friendly_title"]
        file = request.files["file"]

        file_blob = io.BytesIO()
        file.save(file_blob)

        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO file (author_id, friendly_title, contents) VALUES (?, ?, ?)",
                (g.user["id"], title, file_blob.getvalue()),
            )
            db.commit()
            return redirect(url_for("files.index"))

    return render_template("files/create.html")


@bp.route("/<int:id>/download", methods=("GET",))
def download(id):
    #file = get_file(id)
    file = (
        get_db()
        .execute(
            "SELECT f.contents, f.friendly_title, f.id, f.author_id"
            " FROM file f"
            " WHERE f.id = ?",
            (id,),
        )
        .fetchone()
    )

    file_contents = io.BytesIO(file['contents'])

    return send_file(file_contents, download_name=file['friendly_title'])


@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    """Update a post if the current user is the author."""
    file = get_file(id)

    if request.method == "POST":
        title = request.form["friendly_title"]
        file = request.files["file"]
        error = None

        file_blob = io.BytesIO()
        file.save(file_blob)

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "UPDATE file SET contents=?, created=CURRENT_TIMESTAMP, friendly_title=?"
                " WHERE id=?",
                (file_blob.getvalue(), title, id),
            )
            db.commit()
            return redirect(url_for("files.index"))

    return render_template("files/update.html", file=file)


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    """Delete a post.

    Ensures that the post exists and that the logged in user is the
    author of the post.
    """
    get_file(id)
    db = get_db()
    db.execute("DELETE FROM file WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("files.index"))
