from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_from_directory
from . import db
from flask_login import login_required, current_user
from datetime import datetime
from .transformers import generate_caption
from .models import PredictHistory, Statistics
from werkzeug.utils import secure_filename
import zipfile
import os

main = Blueprint('main', __name__)
IMAGE_PATH = os.path.join(os.getcwd(), "images")

@main.route('/')
@login_required
def index():
    user_id = current_user.id
    histories = PredictHistory.query.filter_by(user_id=user_id).order_by(PredictHistory.generated_date.desc())
    if "generation_id" in request.args:
        try:
            generation_id = int(request.args["generation_id"])
        except:
            flash(f"Invalid Generation ID ({request.args['generation_id']})")
            return redirect(url_for("main.index"))
        pred_hist = PredictHistory.query.get(generation_id)
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
    statistics = Statistics.query.filter_by(user_id=user_id).first()
    histories = PredictHistory.query.filter_by(user_id=user_id).order_by(PredictHistory.generated_date.desc())
    return render_template('profile.html', histories=histories, statistics=statistics)

@main.route('/generate_caption', methods=['POST'])
@login_required
def generate():
    user_id = current_user.id
    model = request.form["captioner"]
    edit_id = request.form["edit"]
    if edit_id == "false":                                 # make new generation
        image = request.files["image"]

        last_primary_key = db.session.query(PredictHistory.id).order_by(PredictHistory.id.desc()).first()[0]
        filename = str(last_primary_key + 1) + "_" + image.filename  # add one to get next PK

        caption = generate_caption(image.stream, model)        # use image.stream convert flask image to PIL image

        new_pred_hist = PredictHistory(user_id=user_id, image_file=filename, caption=caption, generated_date=datetime.now())
        db.session.add(new_pred_hist)
        db.session.flush()
        db.session.refresh(new_pred_hist)

        statistics = Statistics.query.filter_by(user_id=user_id).first()
        statistics.image_uploaded += 1
        statistics.sentence_generated += 1
        statistics.character_generated += len(caption)

        image.stream.seek(0)                               # reset pointer so it can be read again and saved
        image.save(os.path.join("images", filename))       # saving file before commit and after add user to prevent file upload or db commit when error

        db.session.commit()
        generation_id = new_pred_hist.id
    else:                                                  # edit current generation
        pred_hist = PredictHistory.query.get(int(edit_id))
        caption = generate_caption(os.path.join("images", pred_hist.image_file), model)
        pred_hist.caption = caption
        pred_hist.generated_date = datetime.now()

        statistics = Statistics.query.filter_by(user_id=user_id).first()
        statistics.sentence_generated += 1
        statistics.character_generated += len(caption)
        db.session.commit()
        generation_id = int(edit_id)
    return jsonify({"generation_id": generation_id, "caption": caption})

@main.route('/delete_history', methods=['POST'])
@login_required
def delete_history():
    generation_id = int(request.form["generation_id"])
    PredictHistory.query.filter_by(id=generation_id).delete()
    db.session.commit()
    return jsonify({"response": "success"})

@main.route('/batch_generate')
@login_required
def batch_generate():
    user_id = current_user.id
    histories = PredictHistory.query.filter_by(user_id=user_id).order_by(PredictHistory.generated_date.desc())
    return render_template('batch_generate.html', histories=histories)

@main.route('/handle_batch', methods=['POST'])
@login_required
def handle_batch():
    user_id = current_user.id
    model = request.form["captioner"]
    images = request.files["imagesFolder"]

    file_like_object = images.stream._file  
    with zipfile.ZipFile(file_like_object, "r") as f:
        for idx, name in enumerate(f.namelist()):
            image = f.open(name)
            last_primary_key = db.session.query(PredictHistory.id).order_by(PredictHistory.id.desc()).first()[0]
            filename = str(last_primary_key + 1) + "_" + name   # add one to get next PK

            caption = generate_caption(image, model)

            new_pred_hist = PredictHistory(user_id=user_id, image_file=filename, caption=caption, generated_date=datetime.now())
            db.session.add(new_pred_hist)

            statistics = Statistics.query.filter_by(user_id=user_id).first()
            statistics.image_uploaded += 1
            statistics.sentence_generated += 1
            statistics.character_generated += len(caption)

            f.extract(name, "images")       # saving file before commit and after add user to prevent file upload or db commit when error
            os.rename(os.path.join("images", name), os.path.join("images", filename))
            print(f"{idx + 1}/{len(f.namelist())} done")
        db.session.commit()

    flash("Images uploaded successfully")
    return jsonify({"response": "success"})

    
