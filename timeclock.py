from flask import Flask, render_template, request, redirect
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import distinct
from moment import momentjs
import os
from datetime import datetime, timedelta

STATIC_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'assets')

app = Flask(__name__, static_folder=STATIC_PATH)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)
app.jinja_env.globals['momentjs'] = momentjs


class Punch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    time = db.Column(db.DateTime())
    status = db.Column(db.Enum('in', 'out', name='status'))

    def __init__(self, name, time=None, status=None):
        self.name = name
        self.time = time or datetime.utcnow()

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


def process_punch_form(form_data):
    full_date, full_time = [item for item in form_data['utc'].split(' ')]
    date = [int(num) for num in full_date.split('-')]
    time = [int(num) for num in full_time.split(':')]
    return form_data['name'], datetime(date[2], date[0], date[1], *time), form_data['status']


@app.route('/')
def ready():
    return render_template('ready.html')


@app.route('/punch/<name>/')
def punch(name):
    new_punch = Punch(name)
    previous_punch = Punch.query.filter_by(
        name=name).order_by(Punch.time.desc()).first()
    context = {'name': name, 'status': new_punch.status}
    if previous_punch:
        time_between = new_punch.time - previous_punch.time
        if time_between.seconds < 120:
            context['timeout'] = str(120 - time_between.seconds)
            return render_template('punch.html', **context)
    db.session.add(new_punch)
    db.session.commit()
    return render_template('punch.html', **context)


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
    if request.method == 'POST':
        start_date = request.form['from']
        end_date = request.form['to']
        punches = Punch.query.filter(Punch.time <= end_date).filter(
            Punch.time >= start_date).order_by(Punch.time.desc())
        return render_template('view.html', punches=punches, to_val=request.form['to'], from_val=request.form['from'])
    punches = Punch.query.order_by(Punch.time.desc())
    return render_template('view.html', punches=punches)


@app.route('/view/totals/', methods=['GET', 'POST'])
def time_totals():
    # Gets distinct people
    people = [name[0]
              for name in db.session.query(Punch.name.distinct()).all()]

    total = {}
    errors = {}

    # Adds people to context object
    context = {'people': sorted(people, key=unicode.lower)}

    # Creates date filters when request is POST
    if request.method == 'POST':
        start_date = request.form['from']
        end_date = request.form['to']
        context['to_val'] = request.form['to']
        context['from_val'] = request.form['from']

    for person in people:
        # Applies date filters when request is POST
        if request.method == 'POST':
            punches = Punch.query.filter_by(
                name=person).filter(Punch.time <= end_date).filter(
                    Punch.time >= start_date).order_by(Punch.time)
        # Or grabs all punches
        else:
            punches = Punch.query.filter_by(
                name=person).order_by(Punch.time)

        time = timedelta()

        for key, punch in enumerate(punches[1:]):
            previous_punch = punches[key]

            # Flags errors for users punched in but not yet punched out
            if punch.status == 'out' and previous_punch.status == 'in':
                time += (
                    punch.time - previous_punch.time)
                errors[person] = False
            elif key == len(punches[1:]) - 1:
                errors[person] = True

            # Calculates totals
            seconds = time.total_seconds()
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            total[person] = '{}:{:02d}'.format(hours, minutes)

        # Flags error if user has only a single in punch
        if len(punches.all()) == 1:
            errors[person] = True

        context['total'] = total
        context['errors'] = errors
    return render_template('totals.html', **context)


if __name__ == "__main__":
    app.debug = True
    app.run()
