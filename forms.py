from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, URL, Email, Length, EqualTo


# ----- SIGN UP FORM ----- #
class RegisterForm(FlaskForm):
    email = StringField("Email address", validators=[DataRequired(), Email()])
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            EqualTo("confirm", message="Passwords must match"),
        ],
    )
    confirm = PasswordField("Repeat Password")
    name = StringField("Name", validators=[Length(min=4, max=25)])
    submit = SubmitField("Register")


# ----- LOGIN FORM ----- #
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


# ----- CREATE POST FORM ----- #
class CreatePostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    img_url = StringField("Image URL", validators=[DataRequired(), URL()])
    body = TextAreaField(
        "Content (Markdown supported)", validators=[DataRequired()]
    )
    submit = SubmitField("Publish")


# ----- COMMENT FORM ----- #
class CommentForm(FlaskForm):
    comment_text = TextAreaField(
        "Comment (Markdown supported)", validators=[DataRequired()]
    )
    submit = SubmitField("Submit Comment")
