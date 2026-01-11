from flask import Blueprint, redirect, render_template, url_for

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def index():
    return redirect(url_for("web.app"))


@web_bp.get("/app")
def app():
    return render_template("pages/app.html")
