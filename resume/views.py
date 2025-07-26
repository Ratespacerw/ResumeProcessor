from django.http import HttpResponse
from rest_framework.views import APIView # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework import status # type: ignore
from PyPDF2 import PdfReader # type: ignore
from io import BytesIO
import re  # Add missing import
import requests  # Add missing import

def welcome(request):
    return HttpResponse("Welcome to the Resume Scoring API!")

class ResumeScoreAPIView(APIView):
    def post(self, request):
        if 'resume' not in request.FILES:
            return Response({'error': 'No resume file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        resume_file = request.FILES['resume']

        # Validate file size (e.g., max 5MB)
        if resume_file.size > 5 * 1024 * 1024:
            return Response({'error': 'File size exceeds 5MB limit.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Validate file type (e.g., PDF, DOCX, TXT)
            print("File name:", resume_file.name)  # Debugging: Print the file name
            if not resume_file.name.endswith(('.pdf', '.docx', '.txt')):
                return Response({'error': 'Unsupported file type.'}, status=status.HTTP_400_BAD_REQUEST)

            # Process the file directly from memory
            file_content = resume_file.read()  # Read the file content into memory
            print("File content type:", type(file_content))  # Debugging: Print the file content type
            pdf_reader = PdfReader(BytesIO(file_content))
            resume_text = ""
            for page in pdf_reader.pages:
                resume_text += page.extract_text()
            # Debugging: Print the first 100 characters of the extracted text
            print(f"Extracted text (first 100 chars): {resume_text[:100]}")

            # Calculate ATS score - pass request to the function
            score = self.calculate_ats_score(resume_text, request)
            return Response({'ats_score': score}, status=status.HTTP_200_OK)

        except Exception as e:
            # Log the error for debugging
            print(f"Error processing file: {e}")
            return Response({'error': f'Error processing resume: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def calculate_ats_score(self, resume_text, request_data):
        # Initialize scores for different categories
        scores = {
            "keywords": 0,
            "education": 0,
            "experience": 0,
            "skills": 0,
            "formatting": 0
        }

        resume_lower = resume_text.lower()

        # 1. Basic keyword relevance (weighted by importance and frequency)
        general_keywords = {
            "experience": 5,
            "education": 3,
            "skills": 5,
            "projects": 3,
            "certifications": 3,
            "achievements": 4,
            "leadership": 4,
            "communication": 3,
            "teamwork": 3,
            "problem solving": 4,
            "analytical": 3,
            "responsible": 2,
            "managed": 3,
            "developed": 3,
            "implemented": 3,
        }

        # Count keyword occurrences (with a cap to prevent keyword stuffing)
        for keyword, weight in general_keywords.items():
            occurrences = resume_lower.count(keyword)
            # Cap at 3 occurrences per keyword to avoid over-counting
            capped_occurrences = min(occurrences, 3)
            scores["keywords"] += capped_occurrences * weight

        # 2. Job-specific keywords (add support for job description matching)
        job_specific_keywords = self.get_job_specific_keywords(request_data)
        for keyword, weight in job_specific_keywords.items():
            if keyword in resume_lower:
                scores["keywords"] += weight

        # 3. Education scoring
        education_terms = ["bachelor", "master", "phd", "degree", "diploma", "university", "college"]
        education_score = sum(3 for term in education_terms if term in resume_lower)

        # Add bonus for prestigious institutions (could be expanded)
        prestigious_schools = ["harvard", "stanford", "mit", "oxford", "cambridge"]
        education_score += sum(5 for school in prestigious_schools if school in resume_lower)

        # Education relevance
        if "computer science" in resume_lower or "information technology" in resume_lower:
            education_score += 5

        scores["education"] = min(education_score, 25)  # Cap at 25

        # 4. Experience scoring
        experience_indicators = [
            "years of experience",
            "year experience",
            "years experience",
            "worked as",
            "work experience"
        ]

        experience_score = sum(4 for indicator in experience_indicators if indicator in resume_lower)

        # Look for experience durations
        experience_matches = re.findall(r'(\d+)[\+]?\s*(?:year|yr)s?', resume_lower)
        if experience_matches:
            # Convert matches to integers and sum them up (capped at 10 years)
            years = sum(min(int(match), 10) for match in experience_matches)
            experience_score += min(years * 2, 20)  # 2 points per year, max 20

        scores["experience"] = min(experience_score, 25)  # Cap at 25

        # 5. Skills scoring - technical skills are often more valuable
        technical_skills = [
            "python", "java", "javascript", "c++", "sql", "aws", "azure",
            "docker", "kubernetes", "react", "angular", "vue", "django",
            "node.js", "tensorflow", "pytorch", "machine learning", "ai"
        ]

        soft_skills = [
            "leadership", "communication", "teamwork", "project management",
            "time management", "problem solving", "critical thinking"
        ]

        # Give more weight to technical skills
        skills_score = sum(4 for skill in technical_skills if skill in resume_lower)
        skills_score += sum(2 for skill in soft_skills if skill in resume_lower)

        scores["skills"] = min(skills_score, 25)  # Cap at 25

        # 6. Formatting and structure checks
        section_headers = [
            "experience", "education", "skills", "projects",
            "certifications", "publications", "summary", "objective"
        ]

        format_score = sum(3 for header in section_headers
                          if f"{header}:" in resume_lower or f"{header}\n" in resume_lower)

        # Check for contact information
        contact_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone number
            r'linkedin\.com\/in\/[\w-]+'  # LinkedIn
        ]

        format_score += sum(4 for pattern in contact_patterns
                           if re.search(pattern, resume_text))

        # Check for reasonable length (not too short, not too long)
        word_count = len(resume_text.split())
        if 300 <= word_count <= 1000:
            format_score += 5

        scores["formatting"] = min(format_score, 20)  # Cap at 20

        # Calculate total score (out of 100)
        total_score = sum(scores.values())
        normalized_score = min(total_score, 100)

        # Return detailed breakdown
        return {
            "total_score": normalized_score,
            "breakdown": scores,
            "feedback": self.generate_feedback(scores)
        }
        
    def get_job_specific_keywords(self, request_data):
        """
        Extract job-specific keywords based on job description or job title if provided.
        Falls back to a general set of keywords if none provided.
        """
        # Check if job description or job title was provided in the request
        job_keywords = {}
        
        # If job_description was provided in the request data
        if hasattr(request_data, 'data') and 'job_description' in request_data.data:
            # Here you would implement NLP to extract keywords from the job description
            # For simplicity, we're returning a general set based on common tech roles
            job_keywords = {
                "api": 4,
                "backend": 4,
                "frontend": 4,
                "full stack": 5,
                "database": 4,
                "cloud": 4,
                "devops": 4,
                "agile": 3,
                "scrum": 3,
                "git": 3,
                "testing": 3,
                "ci/cd": 4,
            }
        # If job_title was provided
        elif hasattr(request_data, 'data') and 'job_title' in request_data.data:
            job_title = request_data.data['job_title'].lower()
            
            # Define keywords for common job titles
            if 'developer' in job_title or 'engineer' in job_title:
                job_keywords = {
                    "algorithm": 4,
                    "api": 4,
                    "code": 3,
                    "software": 4,
                    "development": 3,
                    "testing": 3,
                    "debugging": 3,
                }
            elif 'data' in job_title:
                job_keywords = {
                    "analytics": 4,
                    "statistics": 4,
                    "machine learning": 5,
                    "sql": 4,
                    "python": 4,
                    "visualization": 3,
                    "big data": 4,
                }
            # Add more job categories as needed
        
        # Return general keywords if no specific job info was provided
        if not job_keywords:
            job_keywords = {
                "responsible": 2,
                "team": 2,
                "project": 2,
                "developed": 3,
                "implemented": 3,
                "managed": 3,
                "created": 2,
            }
        
        return job_keywords

    def generate_feedback(self, scores):
        """
        Generate specific feedback based on the score breakdown.
        """
        feedback = []
        
        # Keywords feedback
        if scores["keywords"] < 15:
            feedback.append("Consider adding more relevant industry keywords to your resume.")
        elif scores["keywords"] < 30:
            feedback.append("Your resume contains some relevant keywords, but could benefit from more specific terminology.")
        else:
            feedback.append("Good use of relevant keywords throughout your resume.")
        
        # Education feedback
        if scores["education"] < 10:
            feedback.append("Your education section could be enhanced with more details about degrees and institutions.")
        else:
            feedback.append("Your education details are well presented.")
        
        # Experience feedback
        if scores["experience"] < 10:
            feedback.append("Add more quantifiable achievements and details to your work experience.")
        elif scores["experience"] < 20:
            feedback.append("Your experience section is solid but could benefit from more specific accomplishments.")
        else:
            feedback.append("Your experience section appears comprehensive and well-detailed.")
        
        # Skills feedback
        if scores["skills"] < 10:
            feedback.append("Consider listing more relevant technical and soft skills.")
        elif scores["skills"] < 18:
            feedback.append("Your skills section is good but could highlight more technical proficiencies.")
        else:
            feedback.append("Excellent range of skills highlighted in your resume.")
        
        # Formatting feedback
        if scores["formatting"] < 10:
            feedback.append("Improve your resume structure with clear section headers and better organization.")
        else:
            feedback.append("Your resume is well-structured and formatted appropriately.")
        
        return feedback

class BuildResumeAPIView(APIView):
    def post(self, request):
        try:
            user_data = request.data.get("info", "")  # e.g., "My name is John. I have 2 years experience in web dev."
            if not user_data:
                return Response({"error": "No info provided."}, status=400)

            # Gemini API setup
            API_KEY = "" #Enter key  # Do NOT use in Authorization header
            API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
            
            headers = {
                "Content-Type": "application/json"
            }

            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"Generate a professional resume based on this information:\n{user_data}"}
                        ]
                    }
                ]
            }

            response = requests.post(API_URL, headers=headers, json=payload)

            if response.status_code != 200:
                return Response({"error": "External model failed.", "details": response.text}, status=500)

            result = response.json()
            return Response({"generated_resume": result}, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)