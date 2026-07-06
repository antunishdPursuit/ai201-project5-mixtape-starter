# Mixtape Bug Hunt Submission

## AI Usage

I used AI during Milestone 1 to help inventory the repository, summarize file responsibilities, trace route-to-service data flows, run the documented setup commands, and interpret the untouched baseline test failures. I independently verified the map by reading the source files, running the full test suite, seeding the database, and starting the Flask app with the required app-factory command. No bug fixes were generated or applied during orientation.

## Codebase Map

### Application Entry Point

- `app.py` creates the Flask application, configures SQLAlchemy, registers four blueprints, and creates database tables.
- `seed_data.py` creates the local demonstration data used to reproduce the five reported issues.

### Data Model

- `User` stores identity, friendships, listening streak state, shared songs, ratings, notifications, and playlists.
- `Song` stores music metadata, its original sharer, ratings, listening events, and tags.
- `ListeningEvent` connects a user, song, and listening timestamp.
- `Rating` connects one user to one song with a score from 1 to 5.
- `Playlist` stores playlist metadata and connects to songs through `playlist_entries`, which also stores position, adding user, and timestamp.
- `Notification` stores recipient, type, message body, timestamp, and read state.

### Route Layer

- `routes/songs.py` exposes search, song detail, rating, and listening endpoints.
- `routes/playlists.py` exposes playlist creation, metadata, song retrieval, and song addition.
- `routes/users.py` exposes user profiles, streaks, notifications, and notification updates.
- `routes/feed.py` exposes Friends Listening Now and general activity endpoints.

The route layer validates basic request data, calls the matching service function, converts results to JSON, and maps service errors to HTTP responses.

### Service Layer

- `services/streak_service.py` records listening events and updates consecutive-day streaks.
- `services/feed_service.py` retrieves recent friend listening activity and the broader activity feed.
- `services/search_service.py` searches song titles and artists and retrieves individual songs.
- `services/notification_service.py` creates notifications for playlist additions, stores ratings, and retrieves or updates notifications.
- `services/playlist_service.py` creates playlists and retrieves playlist metadata or ordered songs.

The five reported bugs are intentionally concentrated in the service layer, but each investigation should begin at the public route and follow the call chain inward.

### Tests

- `tests/test_streaks.py` defines the expected consecutive-day streak behavior, including the Saturday-to-Sunday boundary.
- `tests/test_search.py` defines the expectation that a matching song appears only once regardless of tag count.
- `tests/test_playlists.py` defines the expectation that every playlist song is returned in position order.

Untouched baseline result: 10 tests passed and 3 failed. The failures reproduce the Sunday streak reset and the missing final playlist song. Passing tests do not prove the other reported issues are absent because the starter suite does not cover every issue condition.

## Example Data Flow

### Rating A Song

1. A client sends `POST /songs/<song_id>/rate` with `user_id` and `score`.
2. `routes/songs.py` validates the two required fields and calls `notification_service.rate_song()`.
3. `rate_song()` validates the score, song, and user; then creates or updates the `Rating` record.
4. SQLAlchemy commits the change.
5. The route serializes the returned rating as JSON with HTTP `201`.

This flow is relevant to Issue 4 because the public route delegates both rating behavior and any related notification behavior to `notification_service.py`.

## Architectural Patterns

- Flask application factory with optional test configuration.
- Blueprint-per-domain route organization.
- Routes for HTTP concerns and services for business logic.
- SQLAlchemy models and association tables for persistence.
- Model `to_dict()` methods for JSON-ready serialization.
- Dependency flow from routes to services to models/database.
- Pytest fixtures with an in-memory SQLite database for isolated tests.

## Milestone 1 Setup Verification

- [x] Forked the starter repository to `antunishdPursuit/ai201-project5-mixtape-starter`.
- [x] Cloned it under `Coding/codepath/AI201Summer`.
- [x] Created `.venv` and installed `requirements.txt`.
- [x] Seeded the database successfully.
- [x] Created the `bugfix/mixtape` branch.
- [x] Started the app with `flask --app app:create_app run` and verified a live endpoint.
- [x] Read the README, models, routes, services, and tests.
- [x] Recorded the untouched baseline test result.
- [ ] Read the full five issue descriptions in the CodePath project brief.
- [ ] Choose at least three bugs to reproduce in Milestone 2.

## Five Reported Issues

1. My listening streak keeps resetting.
2. Friends Listening Now shows people from yesterday.
3. The same song keeps showing up twice in search.
4. Playlist additions notify the song owner, but ratings do not.
5. The last song in a playlist never shows up.

The repository README provides these titles and affected services. Selection remains pending until the complete CodePath issue descriptions are reviewed.

## Bug Investigations

RCA entries will be added here only after each selected bug is reproduced before its fix.
