from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
from flask_sqlalchemy import SQLAlchemy
import os

# Initialize the Flask application
app = Flask(__name__)

# Configure the application
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf','jpg','jpeg','png'}
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a real secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize the database
db = SQLAlchemy(app)

# Define the Student model
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    grades1 = db.Column(db.Float, nullable=False)
    grades2 = db.Column(db.Float, nullable=False)
    grades3 = db.Column(db.Float, nullable=False)
    
# Function to create and initialize the database
@app.before_request
def create_tables():
    db.create_all()

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Route for the main page
@app.route('/')
def index():
    students = Student.query.all()
    return render_template('index.html', students=students)

# Route for handling file upload
@app.route('/upload', methods=['POST'])
def upload_file():
    print("handing file upload")
    if any(key not in request.files for key in ['file1', 'file2', 'file3']):
        flash("Some files were not uploaded", 'error')
        print("files not uploaded - redirecting to index")
        return redirect(url_for('index'))

    files = [request.files[key] for key in ['file1', 'file2', 'file3']]

    if any(file.filename == '' for file in files):
        flash("Some files were not selected", 'error')
        print("files not selected - redirecting to index")
        return redirect(url_for('index'))

    if all(allowed_file(file.filename) for file in files):
        try:
            print("processing files...")
            filenames = [secure_filename(file.filename) for file in files]
            file_paths = [os.path.join(app.config['UPLOAD_FOLDER'], filename) for filename in filenames]

            for file, file_path in zip(files, file_paths):
                file.save(file_path)

            extracted_texts = [extract_text_from_pdf(file_path) for file_path in file_paths]
            grades1 = calculate_average_from_text(extracted_texts[0])
            grades2 = calculate_average_from_text(extracted_texts[1])
            grades3 = calculate_average_from_text(extracted_texts[2])

            new_student = Student(name=filenames[0], grades1=grades1, grades2=grades2, grades3=grades3)
            db.session.add(new_student)
            db.session.commit()
            print(f"files uplloded and averages calculated:{grades1},{grades2},{grades3}")

            flash(f"Files uploaded and averages calculated: {grades1}, {grades2}, {grades3}", 'success')
        except Exception as e:
            print(f"An error occurred during processing: {str(e)}")
            flash(f"An error occurred during processing: {str(e)}", 'error')
        
    return redirect(url_for('index'))

# Route for classification page
@app.route('/classification')
def classification():
    students = Student.query.all()
    classified_students = []

    for student in students:
        classification = classify_grades((student.grades1, student.grades2, student.grades3))
        classified_students.append((student.name, (student.grades1, student.grades2, student.grades3), classification))

    return render_template('classification.html', classified_students=classified_students)

# Function for text extraction from PDF
def extract_text_from_pdf(pdf_path):
    try:
        text = pytesseract.image_to_string(Image.open(pdf_path))
        return text
    except Exception as e:
        raise RuntimeError(f"Error during text extraction: {str(e)}")

# Function to calculate average from text
def calculate_average_from_text(text):
    grades = [float(grade) for grade in text.split() if grade.replace('.', '', 1).isdigit()]
    average = sum(grades) / len(grades) if grades else 0.0
    return average

# Function to classify grades
def classify_grades(grades):
    average = sum(grades) / len(grades) if grades else 0.0

    if average >= 16:
        return "Excellent"
    elif average >= 14:
        return "Bien"
    elif average >= 12:
        return "Passable"
    else:
        return "Insuffisant"

if __name__ == '__main__':
    app.run(debug=True)
