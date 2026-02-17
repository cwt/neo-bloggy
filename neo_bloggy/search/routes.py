from flask import Blueprint
from neo_bloggy.search import search as search_internal

search_bp = Blueprint("search", __name__)


@search_bp.route("/search", methods=["GET", "POST"])
def search():
    return search_internal()
