"""Tests for rating notification behavior."""

import pytest

from app import create_app, db
from models import Song, User
from services.notification_service import get_notifications, rate_song


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def rating_users_and_song(app):
    """Create a song owner, a different rater, and the owner's song."""
    with app.app_context():
        owner = User(username="owner", email="owner@example.com")
        rater = User(username="rater", email="rater@example.com")
        db.session.add_all([owner, rater])
        db.session.flush()

        song = Song(title="Test Song", artist="Test Artist", shared_by=owner.id)
        db.session.add(song)
        db.session.commit()

        return {"owner_id": owner.id, "rater_id": rater.id, "song_id": song.id}


def test_rating_another_users_song_notifies_owner(app, rating_users_and_song):
    """A song owner should be notified when another user rates their song."""
    ids = rating_users_and_song

    with app.app_context():
        rate_song(ids["rater_id"], ids["song_id"], 5)
        notifications = get_notifications(ids["owner_id"])

        assert len(notifications) == 1
        assert notifications[0]["type"] == "song_rated"
        assert notifications[0]["body"] == "rater rated your song 'Test Song' 5/5."


def test_rating_own_song_does_not_notify_owner(app, rating_users_and_song):
    """A user should not receive a notification for rating their own song."""
    ids = rating_users_and_song

    with app.app_context():
        rate_song(ids["owner_id"], ids["song_id"], 4)

        assert get_notifications(ids["owner_id"]) == []
