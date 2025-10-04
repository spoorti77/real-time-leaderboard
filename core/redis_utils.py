# core/redis_utils.py
import redis
from django.conf import settings
from django.db.models import F

# --- Configuration Constants ---
# Key for the Sorted Set where the leaderboard data lives in Redis
LEADERBOARD_KEY = 'global_leaderboard'

# Initialize Redis Connection
try:
    redis_conn = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True # Ensure strings are returned instead of bytes
    )
    # Ping to check connection immediately
    redis_conn.ping()
    print("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    print(f"Error connecting to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}. Please ensure Redis server is running. Error: {e}")
    # Set to None or a mock object if connection fails to prevent application crash
    redis_conn = None 

class LeaderboardManager:
    """
    Manages all interactions with the Redis Sorted Set used for the leaderboard.
    A Sorted Set (ZSET) is ideal for leaderboards because it keeps data sorted 
    by score and allows efficient retrieval of ranks and slices.
    """

    def __init__(self):
        self.r = redis_conn
        if not self.r:
            # Raise an error or log a warning if Redis is not connected
            # For this tutorial, we will rely on the print above.
            pass

    def update_user_score(self, user_id: str, new_total_score: int):
        """
        Updates a user's score in the Redis leaderboard.
        The score is the total_score, and the member is the user's ID.
        
        Note: In Redis ZSETs, higher scores are better by default.
        """
        if self.r:
            # ZADD adds the member (user_id) with the score (new_total_score)
            # If the member exists, the score is updated.
            self.r.zadd(LEADERBOARD_KEY, {user_id: new_total_score})

    def get_top_users(self, count: int = 100):
        """
        Retrieves the top 'count' users from the leaderboard, including their rank and score.
        Uses ZREVRANGE to get elements from highest score to lowest score (reverse order).
        """

        end_index = count - 1  # Redis uses 0-based indexing
        
        if self.r:
            # ZREVRANGEBYSCORE: returns (member, score) pairs
            # REV: means highest scores first (descending)
            # WITHSCORS: includes the score with the member (user_id)
            top_scores_data = self.r.zrevrange(
                LEADERBOARD_KEY, 
                0, 
                end_index, 
                withscores=True
            )
            
            # Convert the list of (user_id, score) tuples into a list of dicts
            leaderboard_data = []
            for rank, (user_id, score) in enumerate(top_scores_data, start=1):
                leaderboard_data.append({
                    'rank': rank,
                    'user_id': user_id,
                    # Redis stores scores as floats, convert back to int for scores
                    'score': int(score) 
                })
            return leaderboard_data
        return []

    def get_user_rank_and_score(self, user_id: str):
        """
        Retrieves a user's rank and score.
        ZREVRANK returns the rank (0-indexed, highest score first).
        """
        if self.r:
            # ZREVRANK: Gets the 0-indexed rank (higher score = lower rank index)
            rank_index = self.r.zrevrank(LEADERBOARD_KEY, user_id)
            
            if rank_index is not None:
                # Add 1 to get the human-readable rank
                rank = rank_index + 1
                
                # ZSCORE: Gets the score associated with the member
                score = self.r.zscore(LEADERBOARD_KEY, user_id)
                
                return {
                    'rank': rank,
                    'score': int(score) if score is not None else 0
                }
        return {'rank': None, 'score': 0}

# Instantiate the manager for use in signals and views
leaderboard_manager = LeaderboardManager()