# core/serializers.py
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import CustomUser, ScoreSubmission

# --- 1. Custom JWT Serializer (Already done in Step 3) ---

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    # ... (Keep the existing implementation) ...
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        token['first_name'] = user.first_name
        token['total_score'] = user.total_score
        
        
        return token

# --- 2. Score Submission Serializer (For POSTing new scores) ---

class ScoreSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreSubmission
        # We only need 'score' and 'game_level' from the client
        fields = ('score', 'game_level')
        # 'player' and 'timestamp' are set automatically in the view
        
    def validate_score(self, value):
        """
        Check that the score is a positive integer.
        """
        if value <= 0:
            raise serializers.ValidationError("Score must be a positive number.")
        return value

# --- 3. Leaderboard Data Serializer (For GETting Redis data) ---

class LeaderboardEntrySerializer(serializers.Serializer):
    """
    Serializer for displaying the leaderboard data retrieved from Redis.
    This is NOT a ModelSerializer.
    """
    rank = serializers.IntegerField()
    user_id = serializers.UUIDField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    score = serializers.IntegerField()