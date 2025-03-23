import os
import re
from flask import Flask, render_template, request, redirect, url_for, flash, session
from pdfminer.high_level import extract_text
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'resumes/'
app.secret_key = 'a_very_long_and_random_secret_key_123456789'

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'gokulprakash1109@gmail.com'  # Replace with your Gmail address
app.config['MAIL_PASSWORD'] = 'tpcc aueq wnym gjep'  # Replace with your App Password

# Initialize Flask-Mail
mail = Mail(app)

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Step 1: Define job requirements
required_skills = ["Java", "Spring", "Hibernate", "MySQL"]
preferred_certificates = ["Oracle Certified Java Programmer", "Spring Certified", "AWS Certified", 
                         "Microsoft Certified", "Hibernate Certification", "MySQL Certification"]
min_experience_years = 2

# Step 2: Define function to extract skills from resume
def extract_skills(resume_text):
    resume_skills = [skill for skill in required_skills if skill.lower() in resume_text.lower()]
    return resume_skills

# Step 3: Define function to extract email from resume
def extract_email(resume_text):
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    email = re.search(email_pattern, resume_text)
    return email.group(0) if email else None

# Step 4: Define function to extract certificates
def extract_certificates(resume_text):
    certificates = []
    for cert in preferred_certificates:
        if cert.lower() in resume_text.lower():
            certificates.append(cert)
    
    # Look for other certification patterns
    cert_patterns = [
        r'certified\s+[a-zA-Z\s]+\b',
        r'[a-zA-Z]+\s+certification',
        r'certificate\s+in\s+[a-zA-Z\s]+\b'
    ]
    
    for pattern in cert_patterns:
        matches = re.finditer(pattern, resume_text.lower())
        for match in matches:
            cert = match.group(0).title()
            if cert not in certificates and not any(c.lower() in cert.lower() for c in certificates):
                certificates.append(cert)
    
    return certificates

# Step 5: Define function to extract experience
def extract_experience(resume_text):
    # Look for experience patterns like "X years experience" or "X+ years"
    exp_patterns = [
        r'(\d+)[\+]?\s+years?\s+(?:of\s+)?experience',
        r'experience\s+(?:of\s+)?(\d+)[\+]?\s+years?'
    ]
    
    max_years = 0
    for pattern in exp_patterns:
        matches = re.finditer(pattern, resume_text.lower())
        for match in matches:
            years = int(match.group(1))
            max_years = max(max_years, years)
    
    return max_years

# Step 6: Calculate match percentage
def calculate_match_percentage(skills, certificates, experience_years):
    # Skills account for 50% of the score
    skill_score = len(skills) / len(required_skills) * 50
    
    # Certificates account for 30% of the score (max 3 certificates for full score)
    cert_score = min(len(certificates), 3) / 3 * 30
    
    # Experience accounts for 20% of the score (max 5 years for full score)
    exp_score = min(experience_years, 5) / 5 * 20
    
    return round(skill_score + cert_score + exp_score, 2)

# Step 7: Define function to send email confirmation using Flask-Mail
def send_email_confirmation(to_email, match_percentage):
    try:
        # Generate interview date (next Monday)
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # If today is Monday, schedule for next Monday
        interview_date = today + timedelta(days=days_until_monday)
        formatted_date = interview_date.strftime("%A, %B %d, %Y")
        interview_time = "10:00 AM"
        
        # Company info
        company_name = "TechInnovate Solutions"
        company_address = "123 Technology Park, Innovation Tower, 4th Floor, Chennai - 600042"
        
        msg = Message(subject=f"Congratulations! Interview Invitation from {company_name}",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[to_email])
        
        msg.body = f"""Dear Candidate,

Congratulations! We are pleased to inform you that you have been selected for the first level of our recruitment process based on your resume evaluation with a match percentage of {match_percentage}%.

We would like to invite you to our office for the second round of assessment which will include an aptitude test followed by a personal interview.

Interview Details:
Company: {company_name}
Date: {formatted_date}
Time: {interview_time}
Venue: {company_address}

Please bring your resume along with all original certificates for verification.

If you successfully pass both rounds, you will be offered a position with our company.

We look forward to meeting you. Please confirm your attendance by replying to this email.

Best regards,
HR Department
{company_name}
"""
        
        # Send the email
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# Step 8: Route for the home page and resume upload
@app.route('/')
def index():
    return render_template('index.html', required_skills=required_skills)

# Step 9: Handle file upload and processing
@app.route('/upload', methods=['POST'])
def upload_resume():
    # Get parameters from form
    min_percentage = float(request.form.get('min_percentage', 0))
    employees_needed = int(request.form.get('employees_needed', 1))
    
    # Check if the post request has the file part
    if 'resumes' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))
    
    files = request.files.getlist('resumes')
    
    if not files or files[0].filename == '':
        flash('No selected files')
        return redirect(url_for('index'))
    
    results = []
    
    for resume_file in files:
        if resume_file and resume_file.filename != '':
            # Save resume file
            filename = secure_filename(resume_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume_file.save(filepath)
            
            # Extract text from file
            resume_text = ""
            try:
                if filename.endswith('.pdf'):
                    resume_text = extract_text(filepath)
                else:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                        resume_text = file.read()
            except Exception as e:
                flash(f"Error processing {filename}: {str(e)}")
                continue
            
            # Extract information
            skills = extract_skills(resume_text)
            certificates = extract_certificates(resume_text)
            experience_years = extract_experience(resume_text)
            email = extract_email(resume_text)
            
            # Calculate match percentage
            match_percentage = calculate_match_percentage(skills, certificates, experience_years)
            
            # If below minimum percentage, skip this candidate
            if match_percentage < min_percentage:
                continue
                
            # Prepare result
            result = {
                'filename': filename,
                'skills': skills,
                'missing_skills': list(set(required_skills) - set(skills)),
                'certificates': certificates,
                'experience_years': experience_years,
                'match_percentage': match_percentage,
                'email': email,
                'email_sent': False
            }
            
            results.append(result)
    
    # Sort results by match percentage in descending order
    results.sort(key=lambda x: x['match_percentage'], reverse=True)
    
    # Limit to the number of employees needed
    results = results[:employees_needed]
    
    # Store results in session for the email sending route
    session['results'] = results
    
    return render_template('results.html', 
                          results=results, 
                          required_skills=required_skills, 
                          min_percentage=min_percentage,
                          employees_needed=employees_needed)

# Step 10: Handle sending emails to selected candidates
@app.route('/send_email/<int:candidate_index>', methods=['POST'])
def send_email(candidate_index):
    results = session.get('results', [])
    
    if candidate_index < 0 or candidate_index >= len(results):
        flash('Invalid candidate index')
        return redirect(url_for('index'))
        
    candidate = results[candidate_index]
    
    if not candidate.get('email'):
        flash(f"Cannot send email: No email found for {candidate['filename']}")
    else:
        success = send_email_confirmation(candidate['email'], candidate['match_percentage'])
        if success:
            flash(f"Email sent successfully to {candidate['email']}")
            results[candidate_index]['email_sent'] = True
            session['results'] = results
        else:
            flash(f"Failed to send email to {candidate['email']}")
    
    return redirect(url_for('show_results'))

# Step 11: Show results page without reprocessing
@app.route('/results')
def show_results():
    results = session.get('results', [])
    if not results:
        flash('No results to display')
        return redirect(url_for('index'))
        
    return render_template('results.html', 
                          results=results, 
                          required_skills=required_skills)

if __name__ == '__main__':
    app.run(debug=True)