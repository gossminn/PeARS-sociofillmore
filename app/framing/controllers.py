from flask import Blueprint, jsonify

from app import db
from app.api.models import Suggestions

framing = Blueprint('framing', __name__, url_prefix='/framing')

@framing.route("/femicides/")
def femicides():
    femicide_urls = []
    for s in db.session.query(Suggestions).filter_by(pod="possible_femicides").all():
        femicide_urls.append({"url": s.url, "date_created": s.date_created, "notes": s.notes})

    return jsonify(femicide_urls)
