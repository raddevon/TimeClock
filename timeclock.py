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

    def __init__(self, name, time=None, status=None):
        self.name = name
        self.time = time or datetime.now()

        previous_punch = Punch.query.filter_by(
            name=name).order_by(Punch.time.desc()).first()

        if not status:
            if not previous_punch:
                self.status = 'in'
            elif previous_punch.status == 'in':
                self.status = 'out'
            else:
                self.status = 'in'
        else:
            self.status = status

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
        return datetime(date[2], date[0], date[1], 23, 59, 59)
    else:
        return datetime(date[2], date[0], date[1])


def swap_delimiter(date):
    return date.replace('/', '-')


def process_punch_form(form_data):
    date = [int(num) for num in form_data['date'].split('/')]
    time = [int(num) for num in form_data['time'].split(':')]
    return form_data['name'], datetime(date[2], date[0], date[1], *time), form_data['status']


@app.route('/punch/<name>/')
def punch(name):
    # Will not let Brandon punch. Says 103 seconds
    new_punch = Punch(name)
    previous_punch = Punch.query.filter_by(
        name=name).order_by(Punch.time.desc()).first()
    if previous_punch:
        time_between = new_punch.time - previous_punch.time
        if time_between.seconds < 120:
            return 'You punched too fast. Please wait {} seconds longer before punching again.'.format(str(120 - time_between.seconds)), 403
    db.session.add(new_punch)
    db.session.commit()
    return 'Punch {} recorded at {}'.format(new_punch.status, new_punch.time)


@app.route('/edit/<int:punch_id>/', methods=['GET', 'POST'])
def edit_punch(punch_id):
    punch = Punch.query.get(punch_id)
    if not punch:
        return 'This punch does not exist.', 404
    if request.method == 'POST':
        if request.form['action'] == 'Delete':
            db.session.delete(punch)
            db.session.commit()
            return redirect('/view/')
        punch.name, punch.time, punch.status = process_punch_form(request.form)
        db.session.add(punch)
        db.session.commit()
        return redirect('/view/')
    else:
        context = {
            'name': punch.name,
            'status': punch.status,
            'date': '{}/{}/{}'.format(punch.time.month, punch.time.day, punch.time.year),
            'time': '{:02d}:{:02d}'.format(punch.time.hour, punch.time.minute),
            'id': punch.id
        }
        return render_template('edit.html', operation='edit', **context)


@app.route('/add/', methods=['GET', 'POST'])
def add_punch():
    if request.method == 'POST':
        punch = Punch(*process_punch_form(request.form))
        db.session.add(punch)
        db.session.commit()
        return redirect('/view/')
    return render_template('edit.html', operation='add')


@app.route('/')
def home():
    return redirect('/view/')


@app.route('/view/', methods=['GET', 'POST'])
def all_punches():
    # Filtering is broken
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
        if request.method == 'POST':
            punches = Punch.query.filter_by(
                name=person).filter(Punch.time <= end_date).filter(
                    Punch.time >= start_date).order_by(Punch.time)
        else:
            punches = Punch.query.filter_by(
                name=person).order_by(Punch.time)
        time = timedelta()
        for key, punch in enumerate(punches[1:]):
            previous_punch = punches[key]
            if punch.status == 'out' and previous_punch.status == 'in':
                time += (
                    punch.time - previous_punch.time)
                errors[person] = False
            elif key == len(punches[1:]) - 1:
                errors[person] = True
            seconds = time.total_seconds()
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            total[person] = '{}:{:02d}'.format(hours, minutes)
        context['total'] = total
        context['errors'] = errors
    return render_template('totals.html', **context)


if __name__ == "__main__":
    app.debug = True
    app.run()
