# core/urls.py
from django.urls import path
from .views import ScoreSubmissionCreateView, RealTimeLeaderboardView

urlpatterns = [
    # POST to submit a new score (requires authentication)
    path('submit_score/', ScoreSubmissionCreateView.as_view(), name='submit-score'),
    
    # GET the real-time leaderboard data (publicly readable)
    path('leaderboard/', RealTimeLeaderboardView.as_view(), name='realtime-leaderboard'),
]