from flask import Blueprint, jsonify, redirect, render_template, url_for

from core.openapi import build_openapi_spec

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def index():
    return redirect(url_for("web.app"))


@web_bp.get("/app")
def app():
    return render_template("pages/app.html")


@web_bp.get("/docs")
def docs():
    return render_template("pages/docs.html")


@web_bp.get("/openapi.json")
def openapi_json():
    return jsonify(build_openapi_spec())
