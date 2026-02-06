from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from datetime import date

class HabitForm(FlaskForm):
    name = StringField('Habit Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description')
    frequency = SelectField('Frequency', choices=[('daily', 'Daily'), ('weekly', 'Weekly')])
    goal = IntegerField('Goal (number of completions)', validators=[Optional(), NumberRange(min=1)])
    submit = SubmitField('Create Habit')

class HabitLogForm(FlaskForm):
    completed = BooleanField('Completed')
    notes = TextAreaField('Notes')
    submit = SubmitField('Save')
