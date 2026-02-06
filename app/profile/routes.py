import os
import secrets
from PIL import Image
from flask import Blueprint, render_template, url_for, flash, redirect, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models import User
from app.profile.forms import UpdateProfileForm

profile = Blueprint('profile', __name__)

def save_profile_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/uploads/profile_pics', picture_fn)
    
    # Resize image
    output_size = (150, 150)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    return picture_fn

@profile.route('/profile', methods=['GET', 'POST'])
@login_required
def view_profile():
    return render_template('profile/profile.html', title='Profile')

@profile.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = UpdateProfileForm()
    if form.validate_on_submit():
        if form.profile_pic.data:
            picture_file = save_profile_picture(form.profile_pic.data)
            current_user.profile_pic = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.full_name = form.full_name.data
        current_user.age = form.age.data
        current_user.hobbies = form.hobbies.data
        current_user.bio = form.bio.data
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('profile.view_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.full_name.data = current_user.full_name
        form.age.data = current_user.age
        form.hobbies.data = current_user.hobbies
        form.bio.data = current_user.bio
    return render_template('profile/edit_profile.html', title='Edit Profile', form=form)

@profile.route('/user/<string:username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('profile/user_profile.html', title=f"{user.username}'s Profile", user=user)
