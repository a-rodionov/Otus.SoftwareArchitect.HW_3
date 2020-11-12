import os
import json

from flask import Flask, request
from flask_api import status
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, Optional, Email
from sqlalchemy import create_engine
from prometheus_flask_exporter import PrometheusMetrics

class EditUserForm(FlaskForm):
    firstName = StringField("firstName: ", validators=[DataRequired()])
    lastName = StringField("lastName: ", validators=[DataRequired()])
    email = StringField("email: ", validators=[Email()])
    phone = StringField("phone: ", validators=[DataRequired()])

class CreateUserForm(EditUserForm):
    username = StringField("username: ", validators=[DataRequired()])

app = Flask(__name__)
metrics = PrometheusMetrics(app)

ERROR_UNEXPECTED = 1
ERROR_INPUT_DATA = 2
ERROR_OBJECT_NOT_FOUND = 3

config = {
    'DATABASE_URI': os.environ.get('DATABASE_URI', ''),
    'HOSTNAME': os.environ['HOSTNAME'],
    'APP_NAME': os.environ.get('APP_NAME', 'no name'),
}

@app.route("/")
def hello():
    return 'Application \'' + config['APP_NAME'] + '\' from ' + config['HOSTNAME'] + '!'

@app.route("/health")
def health():
    return '{"status": "ok"}'

@app.route("/config")
def configuration():
    return json.dumps(config)

@app.route('/user', methods=['POST'])
def user_create():
    try:
        createUserForm = CreateUserForm(csrf_enabled=False)
        if createUserForm.validate():
            engine = create_engine(config['DATABASE_URI'], echo=True)
            with engine.connect() as connection:
                result = connection.execute('''insert into users (username, firstName, lastName, email, phone) values(%s, %s, %s, %s, %s) returning id''',
                                            (createUserForm.username.data,
                                             createUserForm.firstName.data,
                                             createUserForm.lastName.data,
                                             createUserForm.email.data,
                                             createUserForm.phone.data))
                return json.dumps({'objectId': result.scalar()})
        else:
            return json.dumps({'code': ERROR_INPUT_DATA, 'message': str(createUserForm.errors)})
    except Exception as exc:
        return json.dumps({'code': ERROR_UNEXPECTED, 'message': str(exc)})



@app.route('/user/<int:userId>', methods=['GET'])
def user_get(userId):
    try:
        engine = create_engine(config['DATABASE_URI'], echo=True)
        rows = []
        with engine.connect() as connection:
            result = connection.execute('''select * from users where id=%s''', userId)
            rows = [dict(r.items()) for r in result]
        return json.dumps(rows)
    except Exception as exc:
        return json.dumps({'code': ERROR_UNEXPECTED, 'message': str(exc)})

@app.route('/user/<int:userId>', methods=['DELETE'])
def user_delete(userId):
    try:
        engine = create_engine(config['DATABASE_URI'], echo=True)
        with engine.connect() as connection:
            result = connection.execute('''delete from users where id=%s returning id''', userId)
            if userId == result.scalar():
                return "User deleted", status.HTTP_204_NO_CONTENT
            else:
                return json.dumps({'code': ERROR_OBJECT_NOT_FOUND, 'message': 'Could not delete user with id = %d, because it does not exist' % userId})
    except Exception as exc:
        return json.dumps({'code': ERROR_UNEXPECTED, 'message': str(exc)})

@app.route('/user/<int:userId>', methods=['PUT'])
def user_edit(userId):
    try:
        editUserForm = EditUserForm(csrf_enabled=False)
        if editUserForm.validate():
            engine = create_engine(config['DATABASE_URI'], echo=True)
            with engine.connect() as connection:
                result = connection.execute('''update users set firstName=%s, lastName=%s, email=%s, phone=%s where id=%s returning id''',
                                            (editUserForm.firstName.data,
                                             editUserForm.lastName.data,
                                             editUserForm.email.data,
                                             editUserForm.phone.data,
                                             userId))
                if userId == result.scalar():
                    return "User updated", status.HTTP_200_OK
                else:
                    return json.dumps({'code': ERROR_OBJECT_NOT_FOUND, 'message': 'Could not edit user with id = %d, because it does not exist' % userId})
        else:
            return json.dumps({'code': ERROR_INPUT_DATA, 'message': str(editUserForm.errors)})
    except Exception as exc:
        return json.dumps({'code': ERROR_UNEXPECTED, 'message': str(exc)})

if __name__ == "__main__":
    app.run(host='0.0.0.0',port='8000')