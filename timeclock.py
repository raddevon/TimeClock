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
        return '<Punch {} {} at {}>'.format(self.status, self.name, self.time.strftime('%m-%d-%y %H:%M'))


def construct_datetime(date, end_date=False):
    if date:
        date = [int(num) for num in date.split('-')]
    elif end_date:
        return datetime.now()
    else:
        return datetime(1900, 1, 1)

    if end_date:
        return datetime(2000 + date[2], date[0], date[1], 23, 59, 59)
    else:
        return datetime(2000 + date[2], date[0], date[1])


def swap_delimiter(date):
    return date.replace('/', '-')


@app.route('/punch/<name>/')
def punch(name):
    new_punch = Punch(name, datetime.now())
    previous_punch = Punch.query.filter_by(
        name=name).order_by(Punch.time.desc()).first()
    if previous_punch:
        time_between = new_punch.time - previous_punch.time
        if time_between.seconds < 120:
            return 'You punched too fast. Please wait {} seconds longer before punching again.'.format(str(120 - time_between.seconds)), 403
    db.session.add(new_punch)
    db.session.commit()
    return 'Punch {} recorded at {}'.format(new_punch.status, new_punch.time)


@app.route('/')
def home():
    return redirect('/view/')


@app.route('/view/', methods=['GET', 'POST'])
def all_punches():
    if request.method == 'POST':
        start_date = construct_datetime(swap_delimiter(request.form['from']))
        end_date = construct_datetime(
            swap_delimiter(request.form['to']), True)
        punches = Punch.query.filter(Punch.time <= end_date).filter(
            Punch.time >= start_date).order_by(Punch.time.desc())
        return render_template('view.html', punches=punches, to_val=request.form['to'], from_val=request.form['from'])
    punches = Punch.query.order_by(Punch.time.desc())
    return render_template('view.html', punches=punches)


@app.route('/view/totals/', methods=['GET', 'POST'])
def time_totals():
    people = [name[0]
              for name in db.session.query(Punch.name.distinct()).all()]
    total = {}
    errors = {}
    context = {'people': sorted(people, key=unicode.lower)}
    if request.method == 'POST':
        start_date = construct_datetime(swap_delimiter(request.form['from']))
        end_date = construct_datetime(
            swap_delimiter(request.form['to']), True)
        context['to_val'] = request.form['to']
        context['from_val'] = request.form['from']
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
