# core/views.py
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import F
from django.contrib.auth import get_user_model # Use this for CustomUser
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer
from rest_framework import serializers # Needed for inline_serializer

# Get the configured custom user model
CustomUser = get_user_model()

# Assuming ScoreSubmission and its serializers exist in your project
from .models import ScoreSubmission 
from .serializers import ScoreSubmissionSerializer, LeaderboardEntrySerializer 
from .redis_utils import leaderboard_manager


class ScoreSubmissionCreateView(generics.CreateAPIView):
    """
    API endpoint to allow authenticated users to submit a new score.
    A JWT token is required in the Authorization header.
    """
    queryset = ScoreSubmission.objects.all()
    serializer_class = ScoreSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Automatically set the 'player' field to the authenticated user
        serializer.save(player=self.request.user)


@extend_schema(
    # Use the decorator to clearly define the response structure for documentation
    responses={
        200: inline_serializer(
            name='LeaderboardResponse',
            fields={
                # Uses the LeaderboardEntrySerializer you defined for the list of top users
                'global_leaderboard': LeaderboardEntrySerializer(many=True),
                
                # Uses the LeaderboardEntrySerializer for the single user's rank/score
                'current_user_rank': LeaderboardEntrySerializer(allow_null=True),
            }
        ),
    },
    examples=[
        OpenApiExample(
            'Leaderboard Example',
            value={
                "global_leaderboard": [
                    {"rank": 1, "user_id": "1", "score": 5000, "username": "alpha_user", "first_name": "Alice"},
                    {"rank": 2, "user_id": "2", "score": 4500, "username": "beta_user", "first_name": "Bob"},
                    # ... more entries
                ],
                "current_user_rank": {
                    "rank": 99, 
                    "user_id": "3", 
                    "score": 100, 
                    "username": "self_user", 
                    "first_name": "Charlie"
                }
            },
            response_only=True
        ),
    ]
)
class RealTimeLeaderboardView(APIView):
    """
    API endpoint to retrieve the global leaderboard from Redis.
    
    The response contains the top 100 users (`global_leaderboard`) and, 
    if the request is authenticated, the current user's specific rank and score 
    (`current_user_rank`).
    """
    permission_classes = [permissions.AllowAny] # <-- Set to AllowAny for public access

    def get(self, request, format=None):
        # 1. Get Top 100 Leaderboard from Redis
        top_scores_data = leaderboard_manager.get_top_users(count=100)
        
        # 2. Get User Details (Username, First Name) from MySQL for the top users
        user_ids = [entry['user_id'] for entry in top_scores_data] 
        
        # Retrieve necessary fields from the database in a single query (optimization)
        user_details = CustomUser.objects.filter(id__in=user_ids).values(
            'id', 'username', 'first_name'
        )
        
        # Convert user_details to a dict for fast lookup using 'id'
        user_details_map = {str(user['id']): user for user in user_details}

        # 3. Merge Redis Data with MySQL Details
        leaderboard_list = []
        for entry in top_scores_data:
            user_id_str = str(entry['user_id'])
            details = user_details_map.get(user_id_str, {})
            
            # Create the final, merged entry
            leaderboard_list.append({
                'rank': entry['rank'],
                'user_id': user_id_str,
                'score': entry['score'],
                'username': details.get('username', 'Unknown User'),
                'first_name': details.get('first_name', ''),
            })

        # 4. Serialize the final list
        leaderboard_serializer = LeaderboardEntrySerializer(leaderboard_list, many=True)

        # 5. Get the requesting user's rank/score (from Redis)
        user_rank_data = None
        if request.user.is_authenticated:
            user_rank_data = leaderboard_manager.get_user_rank_and_score(str(request.user.id))
            
            if user_rank_data:
                # Include username and first name for the current user's entry
                user_rank_data['username'] = request.user.username
                user_rank_data['first_name'] = request.user.first_name
        
        # 6. Construct the final response
        response_data = {
            'global_leaderboard': leaderboard_serializer.data,
            'current_user_rank': user_rank_data,
        }

        return Response(response_data, status=status.HTTP_200_OK)