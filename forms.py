from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
    PasswordField,
    TextAreaField,
    SelectField,
)
from wtforms.validators import (
    DataRequired,
    URL,
    Email,
    Length,
    EqualTo,
    Optional,
)


# Security questions for password recovery
SECURITY_QUESTIONS = [
    ("", "Select a security question..."),
    ("pet", "What was the name of your first pet?"),
    ("school", "What was the name of your elementary school?"),
    ("city", "In what city were you born?"),
    ("mother", "What is your mother's maiden name?"),
    ("book", "What was your favorite book as a child?"),
    ("food", "What is your favorite food?"),
    ("car", "What was your first car?"),
    ("sport", "What is your favorite sport?"),
]


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
    security_question = SelectField(
        "Security Question",
        choices=SECURITY_QUESTIONS,
        validators=[DataRequired()],
    )
    security_answer = StringField(
        "Security Answer", validators=[DataRequired()]
    )
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


# ----- PASSWORD RECOVERY FORM ----- #
class PasswordRecoveryForm(FlaskForm):
    email = StringField("Email address", validators=[DataRequired(), Email()])
    security_question = SelectField(
        "Security Question",
        choices=SECURITY_QUESTIONS,
        validators=[DataRequired()],
    )
    security_answer = StringField(
        "Security Answer", validators=[DataRequired()]
    )
    password = PasswordField(
        "New Password",
        validators=[
            DataRequired(),
            EqualTo("confirm", message="Passwords must match"),
        ],
    )
    confirm = PasswordField("Repeat New Password")
    submit = SubmitField("Reset Password")


# ----- EDIT PROFILE FORM ----- #
class EditProfileForm(FlaskForm):
    name = StringField(
        "Name", validators=[DataRequired(), Length(min=4, max=25)]
    )
    email = StringField("Email address", validators=[DataRequired(), Email()])
    password = PasswordField(
        "New Password",
        validators=[
            Optional(),
            EqualTo("confirm", message="Passwords must match"),
        ],
    )
    confirm = PasswordField("Repeat New Password")
    security_question = SelectField(
        "Security Question",
        choices=SECURITY_QUESTIONS,
        validators=[DataRequired()],
    )
    security_answer = StringField(
        "Security Answer", validators=[DataRequired()]
    )
    submit = SubmitField("Update Profile")
