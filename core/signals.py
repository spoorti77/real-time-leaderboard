# core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
from .models import ScoreSubmission, CustomUser
from .redis_utils import leaderboard_manager
from redis.exceptions import ConnectionError as RedisConnectionError # Add this import if using a standard Redis library

import threading

# Thread Local Storage (TLS) to prevent signal loops
_thread_local = threading.local()

@receiver(post_save, sender=ScoreSubmission)
def update_leaderboard_on_submission(sender, instance, created, **kwargs):
    """
    Signal handler that runs AFTER a ScoreSubmission is saved.
    It recalculates the user's total score and updates Redis.
    """
    if not created:
        # We only care about NEW submissions to avoid processing updates/deletes
        return

    # 1. Get the user (player) associated with the new score submission
    player = instance.player
    
    # Check for re-entrancy (signal loop) on the same thread
    if getattr(_thread_local, 'processing_leaderboard', False):
        return
    
    try:
        _thread_local.processing_leaderboard = True
        
        # 2. Recalculate the user's total score from the database (Atomic Operation)
        # Note: F('score') is often used with update() for atomic operations, 
        # but here we need the Sum() of all scores, so an aggregate query is best.
        
        # Calculate the sum of ALL scores for this player
        score_aggregation = ScoreSubmission.objects.filter(player=player).aggregate(total=Sum('score'))
        new_total_score = score_aggregation['total'] if score_aggregation['total'] is not None else 0

        # 3. Update the CustomUser model's total_score field (Atomicity is critical)
        # We update the field on the database directly to avoid triggering the save() method 
        # of the CustomUser model, which could cause an infinite signal loop if we had a 
        # post_save on CustomUser.
        CustomUser.objects.filter(pk=player.pk).update(total_score=new_total_score)
        
        # 4. Update the Redis Leaderboard
        user_id_str = str(player.id)
        leaderboard_manager.update_user_score(user_id_str, new_total_score)
        
        print(f"Leaderboard updated: User {player.username} total score is now {new_total_score}")
        
    finally:
        # Ensure the lock is released
        if hasattr(_thread_local, 'processing_leaderboard'):
            del _thread_local.processing_leaderboard