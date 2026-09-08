"""ORM models.

Importing this package registers every model on ``Base.metadata``. Alembic's
autogenerate depends on this — ``env.py`` does ``from app.models import Base``.
"""

from app.models.base import Base
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.benben import Benben
from app.models.judgement import JudgementLog
from app.models.ticket import Ticket, TicketReply
from app.models.forum import ForumPost, ForumComment
from app.models.notification import Notification
from app.models.problem import Problem
from app.models.submission import Submission, TestCase

__all__ = ["Base", "User", "RefreshToken", "Benben", "JudgementLog", "Ticket", "TicketReply", "ForumPost", "ForumComment", "Notification", "Problem", "Submission", "TestCase"]
