from flask import Flask, render_template, request, redirect
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import distinct
import os
from datetime import datetime, timedelta

STATIC_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'assets')

app = Flask(__name__, static_folder=STATIC_PATH)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)


class Punch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    time = db.Column(db.DateTime())
    status = db.Column(db.Enum('in', 'out', name='status'))

    def __init__(self, name, time):
        self.name = name
        self.time = time

        previous_punch = Punch.query.filter_by(
            name=name).order_by(Punch.time.desc()).first()

        if not previous_punch:
            self.status = 'in'
        elif previous_punch.status == 'in':
            self.status = 'out'
        else:
            self.status = 'in'

    def __repr__(self):
        return '<Punch {} at {}>'.format(self.name, self.time.strftime('%m-%d-%y %H:%M'))


@app.route('/punch/<name>/')
def punch(name):
    new_punch = Punch(name, datetime.now())
    previous_punch = Punch.query.filter_by(
        name=name).order_by(Punch.time.desc()).first()
    if previous_punch:
        time_between = new_punch.time - previous_punch.time
        if time_between.seconds < 120:
            return 'You punched too fast. Please wait at least 2 minutes before punching again.', 403
    db.session.add(new_punch)
    db.session.commit()
    return 'Punch recorded at {}'.format(new_punch.time)


@app.route('/view/')
def all_punches():
    punches = Punch.query.order_by(Punch.time.desc())
    return render_template('view.html', punches=punches)


@app.route('/view/totals/')
def time_totals():
    people = [name[0]
              for name in db.session.query(Punch.name.distinct()).all()]
    total = {}
    for person in people:
        punches = Punch.query.filter_by(
            name=person).order_by(Punch.time)
        time_in_seconds = 0
        print "Person: {}".format(person)
        for punch in punches:
            print 'Punch: {} {}'.format(punch.time, punch.status)
        for key, punch in enumerate(punches[1:]):
            previous_punch = punches[key]
            if punch.status == 'out' and previous_punch.status == 'in':
                print "Current punch: {}".format(punch.time)
                print "Previous punch: {}\n".format(previous_punch.time)
                time_in_seconds += (punch.time - previous_punch.time).seconds
        total[person] = ':'.join(
            str(timedelta(seconds=time_in_seconds)).split(':')[:2])
    return render_template('totals.html', total=total, people=people)


if __name__ == "__main__":
    app.run()
