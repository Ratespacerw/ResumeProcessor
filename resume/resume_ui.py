import sys
import re
from fpdf import FPDF
from fpdf.enums import XPos, YPos  # Add import for new position enums
import requests
from PyQt5.QtWidgets import ( # type: ignore
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QFileDialog, QTextEdit, QMessageBox
)

# Clean function to remove non-ASCII characters
def clean_text(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

def generate_pdf(response):
    # Creating the PDF
    pdf = FPDF()
    pdf.add_page()

    # Title of the resume
    pdf.set_font("Helvetica", style='B', size=14)  # Using Helvetica instead of Arial
    pdf.cell(200, 10, clean_text("Resume"), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Personal Information Section
    pdf.ln(10)  # Line break
    pdf.set_font("Helvetica", size=12)  # Using Helvetica instead of Arial
    for field in ['name', 'email', 'linkedin', 'github', 'location']:
        if field in response['personal_information']:
            pdf.cell(200, 10, clean_text(f"{field.title()}: {response['personal_information'][field]}"), 
                    new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Summary Section
    pdf.ln(10)
    pdf.set_font("Helvetica", style='B', size=12)
    pdf.cell(200, 10, clean_text("Summary"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, clean_text(response['summary']))

    # Experience Section
    pdf.ln(10)
    pdf.set_font("Helvetica", style='B', size=12)
    pdf.cell(200, 10, clean_text("Experience"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=12)
    for exp in response['experience']:
        pdf.cell(200, 10, clean_text(f"{exp['title']} - {exp['company']}"), 
                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(200, 10, clean_text(f"Location: {exp['location']}"), 
                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(200, 10, clean_text(f"Dates: {exp['dates']}"), 
                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.multi_cell(0, 10, clean_text(exp['description']))
        pdf.ln(5)

        # Responsibilities
        for responsibility in exp['responsibilities']:
            pdf.cell(200, 10, clean_text(f"• {responsibility}"), 
                    new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)

    # Skills Section
    pdf.ln(10)
    pdf.set_font("Helvetica", style='B', size=12)
    pdf.cell(200, 10, clean_text("Skills"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=12)
    for skill in response['skills']:
        pdf.cell(200, 10, clean_text(f"{skill['category']}:"), 
                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.multi_cell(0, 10, clean_text(", ".join(skill['keywords'])))
        pdf.ln(5)

    # Education Section
    pdf.ln(10)
    pdf.set_font("Helvetica", style='B', size=12)
    pdf.cell(200, 10, clean_text("Education"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=12)
    for edu in response['education']:
        pdf.cell(200, 10, clean_text(f"{edu['degree']} - {edu['university']}"), 
                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(200, 10, clean_text(f"Dates: {edu['dates']}"), 
                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(200, 10, clean_text(f"Location: {edu['location']}"), 
                new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Output the PDF
    pdf.output("resume.pdf")

class ResumeApp(QWidget):
    def __init__(self):
        super().__init__()  # Fixed initialization
        self.setWindowTitle("Resume Scorer & Builder")
        self.setGeometry(100, 100, 600, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Resume Scoring Section
        self.upload_label = QLabel("Upload Resume (PDF/DOCX/TXT):")
        self.upload_btn = QPushButton("Choose File")
        self.upload_btn.clicked.connect(self.upload_resume)

        # Resume Building Section
        self.info_input = QTextEdit()
        self.info_input.setPlaceholderText("Enter resume info here...")

        self.generate_btn = QPushButton("Generate Resume")
        self.generate_btn.clicked.connect(self.build_resume)

        layout.addWidget(self.upload_label)
        layout.addWidget(self.upload_btn)
        layout.addWidget(QLabel("Build Resume from Info:"))
        layout.addWidget(self.info_input)
        layout.addWidget(self.generate_btn)

        self.setLayout(layout)

    def upload_resume(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Resume File", "", "Documents (*.pdf *.docx *.txt)")
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    files = {'resume': f}
                    response = requests.post("http://127.0.0.1:8000/api/resume-score/", files=files)

                if response.status_code == 200:
                    data = response.json()
                    score = data.get('ats_score', {}).get('total_score', 'N/A')
                    breakdown = data.get('ats_score', {}).get('breakdown', {})
                    feedback = data.get('ats_score', {}).get('feedback', [])
                    msg = f"Score: {score}\n\nBreakdown: {breakdown}\n\nFeedback:\n" + "\n".join(feedback)
                    QMessageBox.information(self, "Resume Score", msg)
                else:
                    QMessageBox.warning(self, "Error", f"Failed to score resume:\n{response.text}")
            except Exception as e:
                QMessageBox.critical(self, "Exception", str(e))

    def build_resume(self):
        info = self.info_input.toPlainText()
        if not info.strip():
            QMessageBox.warning(self, "Input Required", "Please enter your resume info.")
            return
        try:
            response = requests.post("http://127.0.0.1:8000/api/build-resume/", json={"info": info})
            if response.status_code == 200:
                result = response.json()
                
                # Structure the resume data
                resume_data = {
                    'personal_information': {
                        'name': '',
                        'email': '',
                        'linkedin': '',
                        'github': '',
                        'location': ''
                    },
                    'summary': '',
                    'experience': [],
                    'skills': [],
                    'education': []
                }
                
                # Parse the model's response text
                if 'generated_resume' in result:
                    model_response = result['generated_resume']
                    if isinstance(model_response, list):
                        text_content = model_response[0]
                    else:
                        text_content = model_response['candidates'][0]['content']['parts'][0]['text']
                    
                    # Add the raw text as summary for now
                    resume_data['summary'] = text_content
                    
                    # Generate PDF with the structured data
                    generate_pdf(resume_data)
                    QMessageBox.information(self, "Success", "Resume PDF has been generated!")
                else:
                    QMessageBox.warning(self, "Error", "No resume content generated")
            else:
                QMessageBox.warning(self, "Error", f"Failed to generate resume:\n{response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Exception", str(e))

if __name__ == "__main__":  # Fixed main entry point
    app = QApplication(sys.argv)
    window = ResumeApp()
    window.show()
    sys.exit(app.exec_())

