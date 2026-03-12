# ByteSlot Backend

ByteSlot is a scheduling backend built on Django + DRF. It provides role-based accounts, availability slots, bookings with approval flow, notification emails, and Google Meet integration.

## What this backend does
- Email + password authentication with JWT tokens
- OTP based registration flow
- Availability slot management with buffer rules and overlap checks
- Booking creation and admin approval workflow
- Email notifications (pending, confirmed, cancelled, reminders)
- Google OAuth for login and Google Meet link generation
- Admin dashboard stats and system settings

## Tech stack
- Django 5.2
- Django REST Framework
- SimpleJWT
- Celery + Redis (with celery-beat)
- SQLite (default) or MS SQL Server
- Google APIs (OAuth2, Calendar)

## Project structure
- `accounts/` auth, registration OTP, password reset, user management
- `availability/` slots, validation, buffer rules
- `bookings/` booking flow, approval, cancellation
- `core/` system settings and dashboard data
- `notifications/` email notifications and logs
- `integrations/` Google OAuth and Google Meet
- `config/` Django settings, URLs, Celery config
- `templates/` email templates

## Quickstart (local)
1. Create and activate a virtual environment.
2. Install dependencies.
3. Copy `.env.example` to `.env` and adjust values if needed.
4. Run migrations.
5. Start the server.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Optional admin user:
```bash
python create_admin.py
```
Or:
```bash
python manage.py createsuperuser
```

## Environment variables
Set these in `.env` (see `.env.example` for defaults).

| Key | Purpose |
| --- | --- |
| `SECRET_KEY` | Django secret key |
| `DEBUG` | Debug mode toggle |
| `ALLOWED_HOSTS` | Comma-separated hosts |
| `DB_ENGINE` | `sqlite3` or `mssql` |
| `SQLITE_NAME` | SQLite database path |
| `DB_NAME` | MS SQL Server database name |
| `DB_HOST` | MS SQL Server host |
| `DB_PORT` | MS SQL Server port |
| `DB_USER` | MS SQL Server username |
| `DB_PASSWORD` | MS SQL Server password |
| `DB_DRIVER` | ODBC driver |
| `DB_TRUSTED_CONNECTION` | SQL Server trusted connection |
| `CORS_ALLOWED_ORIGINS` | Frontend origins |
| `CSRF_TRUSTED_ORIGINS` | Frontend origins |
| `CELERY_BROKER_URL` | Redis broker |
| `CELERY_RESULT_BACKEND` | Redis result backend |
| `EMAIL_BACKEND` | Django email backend |
| `EMAIL_HOST` | SMTP host |
| `EMAIL_PORT` | SMTP port |
| `EMAIL_USE_TLS` | TLS toggle |
| `EMAIL_HOST_USER` | SMTP username |
| `EMAIL_HOST_PASSWORD` | SMTP password |
| `DEFAULT_FROM_EMAIL` | From email |
| `GOOGLE_CLIENT_ID` | Google OAuth client id |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Google OAuth redirect URI |

Optional (not in `.env.example` but used in code):
- `FRONTEND_URL` for OAuth redirect fallback in `integrations/views.py`

## Authentication
JWT-based auth using SimpleJWT.

Key endpoints:
- `POST /api/accounts/login/` -> email + password, returns JWT tokens
- `POST /api/accounts/token/refresh/` -> refresh token
- `GET /api/accounts/profile/` -> current user
- `PUT /api/accounts/profile/` -> update current user
- `POST /api/accounts/profile/change-password/` -> change password

## Registration (OTP)
Flow:
1. `POST /api/accounts/register/otp/request/` with `{ email }`
2. `POST /api/accounts/register/` with `{ email, otp, password, password_confirm, first_name, last_name, phone }`

## Password reset
There are two supported flows:

PIN based API flow:
- `POST /api/accounts/password-reset/request/` with `{ email }`
- `POST /api/accounts/password-reset/confirm/` with `{ email, token, new_password, password_confirm }`

Django email link flow:
- `POST /api/accounts/password-reset/` with `{ email }`
- `GET /api/accounts/password-reset-confirm/<uidb64>/<token>/`
- Email templates:
  - `accounts/templates/emails/password_reset_email.txt`
  - `accounts/templates/emails/password_reset_email.html`
  - `accounts/templates/emails/password_reset_subject.txt`

## API overview
All APIs are under `/api/`.

### Accounts
| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/api/accounts/register/` | Register user with OTP |
| POST | `/api/accounts/register/otp/request/` | Request OTP |
| POST | `/api/accounts/login/` | Login |
| GET | `/api/accounts/profile/` | Current user |
| PUT | `/api/accounts/profile/` | Update profile |
| POST | `/api/accounts/profile/change-password/` | Change password |
| POST | `/api/accounts/password-reset/request/` | Request PIN reset |
| POST | `/api/accounts/password-reset/confirm/` | Confirm PIN reset |
| POST | `/api/accounts/password-reset/` | Django reset email |
| GET | `/api/accounts/password-reset-confirm/<uidb64>/<token>/` | Django reset confirm |
| GET | `/api/accounts/manage/users/` | Admin list users |
| POST | `/api/accounts/manage/users/` | Admin create user |
| GET | `/api/accounts/manage/users/<id>/` | Admin user detail |
| PUT | `/api/accounts/manage/users/<id>/` | Admin update user |
| DELETE | `/api/accounts/manage/users/<id>/` | Admin delete user |

### Availability
| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/availability/slots/` | Public available slots |
| GET | `/api/availability/admin/slots/` | Admin slots |
| POST | `/api/availability/admin/slots/` | Create slots |
| GET | `/api/availability/admin/slots/<id>/` | Slot detail |
| PUT | `/api/availability/admin/slots/<id>/` | Update slot |
| DELETE | `/api/availability/admin/slots/<id>/` | Delete slot |
| DELETE | `/api/availability/admin/slots/bulk-delete/<date>/` | Delete all slots for date |

### Bookings
| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/bookings/` | Admin list bookings |
| POST | `/api/bookings/create/` | Create booking (public) |
| GET | `/api/bookings/my/` | Current user bookings |
| GET | `/api/bookings/<id>/` | Booking detail |
| POST | `/api/bookings/<id>/cancel/` | Cancel booking |
| POST | `/api/bookings/<id>/approve/` | Approve booking |
| POST | `/api/bookings/<id>/update-status/` | Update status |

### Core
| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/core/settings/` | System settings |
| PUT | `/api/core/settings/` | Update settings |
| GET | `/api/core/dashboard/` | Dashboard stats |

### Notifications
| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/notifications/logs/` | Notification logs |

### Integrations
| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/integrations/google/auth/` | Admin OAuth connect |
| GET | `/api/integrations/google/login/` | Public Google login |
| GET | `/api/integrations/google/callback/` | OAuth callback |
| GET | `/api/integrations/google/status/` | OAuth status |
| POST | `/api/integrations/google/disconnect/` | Disconnect Google |

## Background jobs
Celery tasks are defined in:
- `notifications/tasks.py` for emails and reminders
- `integrations/tasks.py` for Meet link creation

Schedule:
- Reminder job runs every 15 minutes via Celery Beat (`config/celery.py`)

Note: In `config/settings.py` the celery eager mode is enabled by default:
- `CELERY_TASK_ALWAYS_EAGER = True`
- `CELERY_TASK_EAGER_PROPAGATES = True`
Disable these for production worker mode.

## Email delivery
Email uses `SystemSettings` (DB) if SMTP credentials exist, otherwise falls back to `.env` values.
See `core/models.py` and `notifications/services.py`.

## Google OAuth and Meet
Google login and calendar integration live in `integrations/`.
Meet links are created when an admin confirms a video booking.

## Admin
Django admin is available at `/admin/`.

## Useful scripts
- `create_admin.py` creates a superuser with default credentials
- `check_db.py` basic slot/booking counts
- `debug_google_auth.py` OAuth helper
- `debug_slots.py` availability helper

