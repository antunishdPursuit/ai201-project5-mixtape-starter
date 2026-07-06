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
- [x] Reviewed all five reported issues and the CodePath reproduction hints.
- [x] Chose Issues 1, 4, and 5 for Milestone 2.

## Five Reported Issues

1. My listening streak keeps resetting.
2. Friends Listening Now shows people from yesterday.
3. The same song keeps showing up twice in search.
4. Playlist additions notify the song owner, but ratings do not.
5. The last song in a playlist never shows up.

The repository README provides these titles and affected services. Selection remains pending until the complete CodePath issue descriptions are reviewed.

## Bug Investigations

### Issue 1: My Listening Streak Keeps Resetting

#### How I Reproduced It

I ran only the existing Sunday-boundary regression test against the untouched starter code:

```powershell
python -m pytest tests/test_streaks.py::test_streak_increments_on_sunday -v
```

The test creates a user, records activity at noon UTC on Saturday, June 15, 2024, and then records activity at noon UTC on Sunday, June 16, 2024. The Saturday update correctly sets the streak to `1`. After the consecutive Sunday update, the expected streak is `2`, but the actual streak remains `1`, so the test fails at `tests/test_streaks.py:96`.

I also called `update_listening_streak()` directly with the same controlled dates. The output confirmed the behavior independently of the pytest assertion:

```text
After Saturday: 1
After Sunday:   1
Expected Sunday: 2
```

This confirms the bug is conditional on the Saturday-to-Sunday transition and existed before any project code was changed.

#### How I Found the Root Cause

I traced the request from `POST /songs/<song_id>/listen` to `listen()` in `routes/songs.py`. That route calls `record_listening_event()` in `services/streak_service.py`, which records the listen and passes the timestamp to `update_listening_streak()`. I then followed the streak read path from `GET /users/<user_id>/streak` through `streak()` in `routes/users.py` to `get_streak()`, confirming that the endpoint was returning the incorrectly saved value rather than calculating it incorrectly during retrieval.

#### Root Cause

In `update_listening_streak()`, the consecutive-day branch required both `days_since_last == 1` and `today.weekday() != 6`. Python represents Sunday as weekday `6`, so a valid Saturday-to-Sunday transition skipped the increment branch and entered the fallback branch, which reset the streak to `1`.

#### Fix And Side-Effect Check

I removed the unnecessary Sunday exclusion so every `days_since_last == 1` transition increments the streak. Same-day listens still return without changing the streak, and gaps longer than one day still reset it to `1`.

After the fix, all five streak tests passed:

```powershell
python -m pytest tests/test_streaks.py -q
```

The full suite produced `11 passed, 2 failed`. Both remaining failures are the previously reproduced Issue 5 playlist bug, so the streak fix introduced no new test regressions.

### Issue 4: Rating A Friend's Song Does Not Notify Them

#### How I Reproduced It

I created two users in an isolated in-memory database: one user shared a song and a different user rated it. I submitted the rating through the real `POST /songs/<song_id>/rate` route, then retrieved the original sharer's notifications through `GET /users/<owner_id>/notifications`.

The rating request succeeded and the database contained the expected `Rating` record, but the song owner had no notification:

```text
Rating status: 201
Saved ratings: 1
Owner notifications: 0
Expected notifications: 1
```

This separates the two behaviors: rating persistence works, while the notification side effect is missing. The evidence was collected before changing any application code.

#### How I Found the Root Cause

Pending investigation after Milestone 2 reproduction is complete.

#### Root Cause

Pending investigation. The successful rating and missing notification establish the symptom but do not yet document the cause.

#### Fix And Side-Effect Check

Pending. No application code has been changed for Issue 4.

### Issue 5: The Last Song In A Playlist Never Shows Up

#### How I Reproduced It

I ran the two existing playlist regression tests against the untouched starter code:

```powershell
python -m pytest tests/test_playlists.py::test_playlist_returns_all_songs tests/test_playlists.py::test_playlist_returns_songs_in_order -v
```

Both tests failed. A playlist containing five stored songs returned only four, and the ordered title list ended at `Track 4` instead of including `Track 5`.

I independently created an in-memory playlist with five songs at positions 1 through 5 and called `get_playlist_songs()` directly. The result was:

```text
Stored songs: 5
Returned songs: 4
Returned titles: ['Track 1', 'Track 2', 'Track 3', 'Track 4']
Missing title: Track 5
```

This confirms that the database contains the fifth song and the loss occurs during playlist retrieval, not during insertion. No fix code was applied during reproduction.

#### How I Found the Root Cause

Pending investigation after Milestone 2 reproduction is complete.

#### Root Cause

Pending investigation. The evidence narrows the failure to retrieval but does not yet record the specific cause.

#### Fix And Side-Effect Check

Pending. No application code has been changed for Issue 5.
