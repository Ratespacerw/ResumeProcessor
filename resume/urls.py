from django.urls import path
from . import views

urlpatterns = [
    path('resume-score/', views.ResumeScoreAPIView.as_view(), name='resume-score'),
    path('welcome/', views.welcome, name='welcome'),
    path('build-resume/', views.BuildResumeAPIView.as_view(), name='build-resume'),
]