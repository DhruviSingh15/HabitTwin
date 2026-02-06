from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField, IntegerField, StringField, BooleanField
from wtforms.validators import NumberRange, Optional, DataRequired

class UploadScreenTimeForm(FlaskForm):
    excel_file = FileField('Upload Excel File', validators=[
        FileRequired(),
        FileAllowed(['xlsx'], 'Excel files only!')
    ])
    submit = SubmitField('Upload')

class DigitalDetoxForm(FlaskForm):
    daily_limit = IntegerField('Daily Screen Time Limit (minutes)', 
                               validators=[NumberRange(min=1), DataRequired()])
    enable_app_blocking = BooleanField('Block apps when limit is reached', default=False)
    enable_notifications = BooleanField('Enable notifications', default=True)
    enable_break_reminders = BooleanField('Enable break reminders', default=True)
    break_interval_minutes = IntegerField('Remind me to take a break every (minutes)',
                                        validators=[NumberRange(min=15), Optional()], default=60)
    submit = SubmitField('Start Digital Detox')

class AppLimitForm(FlaskForm):
    app_name = StringField('App Name', validators=[DataRequired()])
    daily_limit_minutes = IntegerField('Daily Limit (minutes)', 
                                      validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Set App Limit')
