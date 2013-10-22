from flask import Flask, render_template
from flask.ext.sqlalchemy import SQLAlchemy
import os
form datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)


class Punch(db.model):
    name = db.Column(db.String(150))
    time = db.Column(db.DateTime())
    status = db.Column(db.Enum('in', 'out'))

    def __init__(self, name, time):
        self.name = name
        self.time = time

        previous_punch = Punch.query.filter_by(
            name=name).order_by(Punch.time.desc()).first()

        if previous_punch.status == 'in':
            self.status = 'out'
        else:
            self.status = 'in'

    def __repr__(self):
        return '<Punch {} at {}>'.format(self.name, self.time.strftime('%m-%d-%y %H:%M'))


@app.route('/punch/<name>')
def punch(name):
    new_punch = Punch(name, datetime.now())
    previous_punch = Punch.query.filter_by(
        name=name).order_by(Punch.time.desc()).first()
    time_between = new_punch - previous_punch

    if time_between > 120:
        db.session.add(new_punch)
        db.session.commit()
    else:
        return 'You punched too fast. Please wait at least 2 minutes before punching again.', 403


@app.route('/view/')
def view():
    punches = Punch.query.all()
    return render_template('view.html', {'punches': punches})


if __name__ == "__main__":
    app.run()
