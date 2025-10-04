# core/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid 

class CustomUser(AbstractUser):
    """
    Custom User Model extending AbstractUser.
    - Login will use the default 'username' field (which is unique).
    - We keep all the new custom fields (user_id, phone_number, total_score).
    """
    email = models.EmailField(_("email address"), unique=True) # Make email unique
    


    # Phone Number (Optional field)
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name=_("Phone Number")
    )

    # Total Score (The field that will be stored in MySQL and mirrored in Redis)
    total_score = models.IntegerField(
        default=0,
        verbose_name=_("Total Accumulated Score")
    )
    
    # REQUIRED_FIELDS are fields required when creating a superuser (in addition to username and password)
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name'] # Email is now required on superuser creation

    def __str__(self):
        # Return the username as it's the primary login identifier
        return self.username 

# ScoreSubmission model remains unchanged and correct
class ScoreSubmission(models.Model):
    """
    Represents a single score submission by a user.
    """
    player = models.ForeignKey(
        CustomUser, # Links to our newly customized user model
        on_delete=models.CASCADE,
        related_name='scores'
    )
    score = models.IntegerField(
        verbose_name=_("Submitted Score")
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Submission Timestamp")
    )
    game_level = models.CharField(
        max_length=50,
        verbose_name=_("Game/Level Identifier"),
        default='default_game'
    )

    class Meta:
        ordering = ['-score', 'timestamp']
        verbose_name = _("Score Submission")
        verbose_name_plural = _("Score Submissions")

    def __str__(self):
        return f"{self.player.username}: {self.score} ({self.game_level})"