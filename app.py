from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to my first API!"

@app.route('/student')
def get_student():
    return jsonify({
        "student_id": "24-00176",
        "name": "Jad Warren Casas",
        "program": "BSIT",
        "year": 3,
        "section": "A"
    })

@app.route('/hello')
def say_hello():
    name = request.args.get('name', 'Student')
    return jsonify({
        "message": f"Hello, {name}!"
    })

@app.route('/course')
def get_course():
    return jsonify({
        "course_code": "IT 301",
        "course_name": "Web Development",
        "units": 3,
        "description": "Introduction to web development and API creation using Flask."
    })

@app.route('/profile')
def get_profile():
    return jsonify({
        "student_id": "24-00176",
        "name": "Jad Warren Casas",
        "program": "BSIT",
        "year": 3,
        "section": "A",
        "course": "Web Development",
        "role": "Student"
    })

@app.route('/greetings')
def greetings():
    name = request.args.get('name', 'Student')
    return jsonify({
        "greeting": f"Good day, {name}!",
        "message": "Welcome to the Flask API."
    })

if __name__ == '__main__':
    app.run(debug=True)
