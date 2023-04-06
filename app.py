from flask import Flask, flash, request, jsonify
from con import set_connection
from loggerinstance import logger
import psycopg2
import json

app = Flask(__name__)


def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except psycopg2.Error as e:
            conn = kwargs.get('conn')
            if conn:
                conn.rollback()
            logger.error(str(e))
            return jsonify({"error": "Database error"})
        except Exception as e:
            logger.error(str(e))
            return jsonify({"error": str(e)})
        finally:
            conn = kwargs.get('conn')
            cur = kwargs.get('cur')
            if cur:
                cur.close()
            if conn:
                conn.close()

    return wrapper

#
# CREATE TABLE students (
#     id SERIAL PRIMARY KEY,
#     name VARCHAR(50) NOT NULL
# );
#
# CREATE TABLE grades (
#     id SERIAL PRIMARY KEY,
#     student_id INTEGER REFERENCES students(id),
#     grade FLOAT(2) NOT NULL
# );


@app.route('/v1/add_student', methods=['POST'], endpoint='add_student')
@handle_exceptions
def add_student():
    # {
    #     "name": "Akshith",
    #     "grades": {
    #         "maths": 95,
    #         "physics": 99,
    #         "chemistry": 96
    #     }
    # }
    student_name = request.json['name']
    student_grades = request.json['grades']
    cur, conn = set_connection()

    # Convert grades to JSON string
    student_grades_str = json.dumps(student_grades)

    # Insert the new student into the database
    insert_query = "INSERT INTO students (name, grades) VALUES (%s, %s)"
    cur.execute(insert_query, (student_name, student_grades_str))
    conn.commit()
    logger.info("Added student successfully")

    return jsonify({'message': 'Student added successfully'})


@app.route('/v1/calculate_average/<string:name>', methods=['GET'], endpoint='calculate_average')
@handle_exceptions
def calculate_average(name):
    cur, conn = set_connection()
    select_query = "SELECT grades FROM students WHERE name=%s"
    cur.execute(select_query, (name,))
    result = cur.fetchone()

    if result:
        grades_json = result[0]
        try:
            grades = json.loads(grades_json)
        except json.JSONDecodeError:
            return jsonify({'message': 'Error decoding grades JSON'}), 400

        if not isinstance(grades, list):
            return jsonify({'message': 'Grades field is not a list'}), 400

        if not grades:
            return jsonify({'message': 'No grades found for student'}), 404

        average = sum(grades) / len(grades)
        logger.info(f"Calculated average{average}")
        return jsonify({'average': average})
    else:
        return jsonify({'message': 'Student not found'}), 404


@app.route('/v1/generate_report', methods=['GET'], endpoint='generate_report')
@handle_exceptions
def generate_report():
    cur, conn = set_connection()
    # Retrieve all students from database
    cur.execute("SELECT id, name FROM students")
    students = cur.fetchall()
    if not students:
        return jsonify({'message': 'No students found'})
    # Iterate over students and retrieve grades from database
    report = []
    for student in students:
        student_id = student[0]
        student_name = student[1]
        cur.execute("SELECT grade FROM grades WHERE student_id=%s", (student_id,))
        grades = cur.fetchall()
        if not grades:
            continue
        grades = [grade[0] for grade in grades]
        average = sum(grades) / len(grades)
        report.append({'name': student_name, 'grades': grades, 'average': average})
    logging.info("Generated report Successfully")
    return jsonify({'report': report})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
