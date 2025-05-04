from flask_wtf import FlaskForm  # FlaskForm integrates CSRF protection automatically
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class TransferForm(FlaskForm):
    """
    Transfer form that includes CSRF protection and field-level validation.
    CSRF protection helps prevent cross-site request forgery attacks.
    """

    # Source account field - required
    source = StringField('From', validators=[DataRequired()])

    # Target account field - required
    target = StringField('To', validators=[DataRequired()])

    # Amount field - must be an integer and between 1 and 1000
    amount = IntegerField('Amount', validators=[
        DataRequired(message="Please enter an amount"),
        NumberRange(min=1, max=1000, message="Amount must be between 1 and 1000")
    ])

    # Submit button
    submit = SubmitField('Transfer')
