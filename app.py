import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for, g)
from flask_ckeditor import CKEditor
from flask_bootstrap import Bootstrap
from forms import RegisterForm, LoginForm, CreatePostForm, CommentForm
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import neosqlite

if os.path.exists("env.py"):
    import env

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")
Bootstrap(app)
ckeditor = CKEditor(app)

# Configure CKEditor to serve locally
app.config['CKEDITOR_SERVE_LOCAL'] = True
app.config['CKEDITOR_PKG_TYPE'] = 'standard'

# Database configuration
DB_PATH = os.environ.get("DB_PATH", "/tmp/neosqlite.db")

def get_db():
    """Get database connection for the current request."""
    if 'db' not in g:
        g.db = neosqlite.Connection(DB_PATH)
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Close database connection at the end of the request."""
    if 'db' in g:
        g.db.close()
        g.pop('db', None)


# ---------------- #
#    APP ROUTES    #
# ---------------- #

# ----- HOME ----- #
@app.route("/")
def get_all_posts():
    '''
    Read all blog posts from the database.
    '''
    db = get_db()
    posts = list(db.blog_posts.find())
    return render_template("index.html", all_posts=posts)


# ----- REGISTER ----- #
@app.route('/register', methods=["GET", "POST"])
def register():
    '''
    Sign up for a new account.
    '''
    form = RegisterForm()
    if form.validate_on_submit():
        db = get_db()
        users = db.users

        # check if email already exists in database
        existing_user = users.find_one(
            {"email": form.email.data})

        if existing_user:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        # hash and salt the password
        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = {
            "email": form.email.data,
            "password": hash_and_salted_password,
            "name": form.name.data
        }
        # insert new_user into the database
        users.insert_one(new_user)

        # put the new user into 'session' cookie
        session["user"] = form.name.data
        flash("Registration Successful")
        return redirect(url_for("profile", username=session["user"]))
    return render_template("register.html", form=form)


# ----- LOGIN ----- #
@app.route('/login', methods=["GET", "POST"])
def login():
    '''
    Login to the site.

    Validation included.
    '''
    form = LoginForm()
    if form.validate_on_submit():
        db = get_db()
        users = db.users
        email = form.email.data
        password = form.password.data

        # check if email already exists
        existing_user = users.find_one({"email": email})
        # if email doesn't exist or password incorrect
        if not existing_user:
            flash("That email or password does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(existing_user["password"], password):
            flash('That email and password dont match, please try again.')
            return redirect(url_for('login'))
        else:
            session["user"] = existing_user['name']
            flash(f"Welcome Back, {existing_user['name'].capitalize()}")
            return redirect(
                url_for("profile", username=session["user"]))
    return render_template("login.html", form=form)


# ----- PROFILE PAGE ----- #
@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    '''
    Direct the user to their Profile page.

    Retrieve all the users Posts.
    '''
    db = get_db()
    user = db.users.find_one(
        {"name": session["user"]})
    username = user["name"] if user else username
    posts = db.blog_posts.find({"author": username})
    # if logged in
    if session["user"]:
        return render_template("profile.html", username=username, posts=posts)
    # if not logged in, return to login page
    return redirect(url_for("login"))


# ----- LOGOUT ----- #
@app.route("/logout")
def logout():
    '''
    Logout the user.

    Redirect the user to the home page.
    '''
    session.pop("user")
    return redirect(url_for("get_all_posts"))


# ----- READ A POST BY ITS ID ----- #
@app.route("/post/<post_id>", methods=["GET", "POST"])
def show_post(post_id):
    '''
    Read a Post by Id.

    Allow the user to Comment if logged in.
    '''
    form = CommentForm()
    db = get_db()
    # find the requested post
    requested_post = db.blog_posts.find_one({"_id": int(post_id)})
    requested_post_comments = db.blog_comments.find(
        {"parent_post": int(post_id)})

    # commenting on a post
    if form.validate_on_submit():
        if not session["user"]:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        new_comment = {
            "text": form.comment_text.data,
            "comment_author": session["user"],
            "parent_post": int(post_id)
        }

        db.blog_comments.insert_one(new_comment)
    return render_template("post.html", post=requested_post,
                           comments=requested_post_comments, form=form)


# ----- CREATE A NEW POST ----- #
@app.route("/create-post", methods=["GET", "POST"])
def create_post():
    '''
    Create a new Post.

    Inject all form data to a new blog post document on submit.
    '''
    if "user" in session:
        # create a Form for data entry
        form = CreatePostForm()
        if form.validate_on_submit():
            db = get_db()
            new_post = {
                "title": form.title.data,
                "subtitle": form.subtitle.data,
                "body": form.body.data,
                "img_url": form.img_url.data,
                "author": session["user"],
                "date": date.today().strftime("%B %d, %Y")
            }
            db.blog_posts.insert_one(new_post)
            flash("Post Successfully Added")
            return redirect(url_for("get_all_posts"))
        return render_template("create_post.html", form=form)
    else:
        return redirect(url_for("login"))


# ----- EDIT A POST BY ID ----- #
@app.route("/edit-post/<post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    '''
    Edit a Post by Id.

    Update all Post data on submit.
    '''
    db = get_db()
    post = db.blog_posts.find_one({"_id": int(post_id)})

    edit_form = CreatePostForm(
        title=post["title"],
        subtitle=post["subtitle"],
        img_url=post["img_url"],
        author=session["user"],
        body=post["body"]
    )
    if edit_form.validate_on_submit():
        db.blog_posts.update_one({"_id": int(post_id)}, {"$set": {
            "title": edit_form.title.data,
            "subtitle": edit_form.subtitle.data,
            "img_url": edit_form.img_url.data,
            "body": edit_form.body.data
        }})
        return redirect(url_for("show_post", post_id=post_id))
    return render_template("create_post.html", form=edit_form, is_edit=True)


# ----- DELETE A POST BY ID ----- #
@app.route("/delete/<post_id>")
def delete_post(post_id):
    '''
    Delete a Post by Id.

    Redirect back to main page on submit.
    '''
    db = get_db()
    db.blog_posts.delete_one({"_id": int(post_id)})
    flash("Post Successfully Deleted")
    return redirect(url_for('get_all_posts'))


# ----- DELETE A COMMENT BY ID ----- #
@app.route("/delete_comment/<comment_id>")
def delete_comment(comment_id):
    '''
    Delete a Comment by Id.
    '''
    db = get_db()
    db.blog_comments.delete_one({"_id": int(comment_id)})
    flash("Comment Successfully Deleted")
    post_id = request.args.get('post_id')
    return redirect(url_for("show_post", post_id=post_id))


# ----- SEARCH FOR A POST BY TITLE, SUBTITLE ----- #
@app.route("/search", methods=["GET", "POST"])
def search():
    '''
    Search for a Post by Title, Subtitle.
    '''
    db = get_db()
    query = request.form.get("query")
    # For neosqlite, we'll use a simple text search on title and subtitle
    # Using a more compatible approach with basic string matching
    if query:
        # Get all posts and filter in Python as a workaround
        all_posts = list(db.blog_posts.find())
        posts = [post for post in all_posts 
                if query.lower() in post.get("title", "").lower() or 
                   query.lower() in post.get("subtitle", "").lower()]
    else:
        posts = list(db.blog_posts.find())
    return render_template("index.html", all_posts=posts)


# ----- HANDLE 404 ERROR ----- #
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# ----- HANDLE 403 ERROR ----- #
@app.errorhandler(403)
def page_not_found(e):
    return render_template('403.html'), 403


# ----- HANDLE 500 ERROR ----- #
@app.errorhandler(500)
def page_not_found(e):
    return render_template('500.html'), 500


if __name__ == "__main__":
    app.run(host=os.environ.get("IP", "127.0.0.1"),
            port=int(os.environ.get("PORT", 5000)),
            debug=True)
