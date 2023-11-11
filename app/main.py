from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_from_directory
from . import db
from flask_login import login_required, current_user
from datetime import datetime
from .transformers import generate_caption
from .models import PredictHistory
from werkzeug.utils import secure_filename
import os

main = Blueprint('main', __name__)
IMAGE_PATH = os.path.join(os.getcwd(), "images")

@main.route('/')
@login_required
def index():
    user_id = current_user.id
    histories = PredictHistory.query.filter_by(user_id=user_id)
    if "generation_id" in request.args:
        generation_id = request.args["generation_id"]
        pred_hist = PredictHistory.query.get(int(generation_id))
        if not pred_hist:
            flash("This generation doesn't exist or already deleted")
            return redirect(url_for("main.index"))
        return render_template('index.html', histories=histories, image_path=pred_hist.image_file, caption=pred_hist.caption)
    else:
        return render_template('index.html', histories=histories, image_path="", caption="")

@main.route('/load_image/<path:filename>')
def load_image(filename):
    return send_from_directory(IMAGE_PATH, filename, as_attachment=True)

@main.route('/profile')
@login_required
def profile():
    user_id = current_user.id
    histories = PredictHistory.query.filter_by(user_id=user_id)
    return render_template('profile.html', histories=histories)

@main.route('/generate_caption', methods=['POST'])
@login_required
def generate():
    user_id = current_user.id

    image = request.files["image"]
    extension = image.filename.split('.')[1]
    filename = str(user_id) + "_" + datetime.now().strftime("%d_%m_%Y_%H_%M_%S") + "." + extension

    model = request.form["captioner"]
    caption = generate_caption(image, model)

    new_pred_hist = PredictHistory(user_id=user_id, image_file=filename, caption=caption, generated_date=datetime.now())
    db.session.add(new_pred_hist)
    db.session.flush()
    db.session.refresh(new_pred_hist)

    image.stream.seek(0)                               # reset pointer so it can be read again and saved
    image.save(os.path.join("images", filename))       # saving file before commit and after add user to prevent file upload or db commit when error

    db.session.commit()
    return jsonify({"generation_id": new_pred_hist.id, "caption": caption})