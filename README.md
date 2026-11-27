# Django Job Portal — Web Application & REST API

A full-stack Job Portal built with **Python, Django, Django REST Framework (DRF), and MySQL**.

The application supports job seekers and employers with role-based access control, job management, applications, profile management, and REST API integration.

## Features

### Authentication & Authorization
- User registration and login
- Token-based API authentication
- Role-based access for job seekers and employers
- Custom DRF permissions
- Job ownership validation

### Job Management
- Create, update, delete, and view job listings
- Search jobs by keyword
- Filter by location and salary range
- Sort job listings
- Custom pagination

### Application Management
- Job seekers can apply for jobs
- Prevent duplicate applications
- Employers can view applicants
- Employers can accept or reject applications
- Email notifications for application status changes

### Profile Management
- User profile management
- Role-based profiles
- Resume upload
- Profile information updates

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Django | Web framework |
| Django REST Framework | REST API development |
| MySQL | Database |
| HTML / CSS | Frontend |
| Postman | API testing |
| Pytest / Django Tests | Automated testing |

## Project Structure

```text
django-job-portal/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── jobs/
│   ├── migrations/
│   ├── templates/
│   ├── tests/
│   ├── models.py
│   ├── serializers.py
│   ├── permissions.py
│   ├── pagination.py
│   ├── signals.py
│   ├── notifications.py
│   ├── views.py
│   ├── urls.py
│   └── api_urls.py
│
├── manage.py
├── pytest.ini
├── requirements.txt
└── README.md
```

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/abdulvajeth12/django-job-portal.git
cd django-job-portal
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root.

You can use `.env.example` as a reference if provided in the repository.

Example:

```env
SECRET_KEY=your_django_secret_key
DB_NAME=all_job_portal_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
```

Make sure the environment variable names match `config/settings.py`.

**Never commit your actual `.env` file, secret key, or database credentials.**

### 5. Create the MySQL database

```sql
CREATE DATABASE all_job_portal_db;
```

Ensure MySQL is running and the database credentials match your `.env` file.

### 6. Run database migrations

```bash
python manage.py migrate
```

### 7. Start the development server

```bash
python manage.py runserver
```

Open:

http://127.0.0.1:8000/

## REST API Endpoints

Base URL:

```text
http://127.0.0.1:8000/api/
```

| Method | Endpoint | Description |
|---|---|---|
| GET | `/jobs/` | List and filter jobs |
| POST | `/jobs/create/` | Create a job |
| GET | `/jobs/<slug>/` | Retrieve job details |
| PUT/PATCH | `/jobs/<slug>/update/` | Update a job |
| DELETE | `/jobs/<slug>/delete/` | Delete a job |
| POST | `/register/` | Register a user |
| POST | `/login/` | Authenticate a user |
| GET/PATCH | `/profile/` | Retrieve or update profile |
| POST | `/jobs/<slug>/apply/` | Apply for a job |
| GET | `/my-applications/` | View own applications |

### Authentication

The API uses token authentication.

Include the token returned by the login API in the request header:

```http
Authorization: Token YOUR_AUTH_TOKEN
```

### Job Filtering Example

```http
GET /api/jobs/?search=Python&location=Chennai&min_salary=20000
```

## Testing

The project includes automated tests for API and web application functionality.

Run Django tests:

```bash
python manage.py test
```

Run pytest:

```bash
pytest
```

Postman was also used for manual API testing, including authentication, permissions, validation, and error handling.

## Key Engineering Focus

- Custom role-based permissions
- Employer ownership validation
- Prevention of unauthorized job modifications
- API input validation and error handling
- Search, filtering, ordering, and pagination
- Automated testing of API and application workflows

## Future Improvements

- Docker and Docker Compose
- Deployment to a cloud platform
- CI/CD integration
- API documentation with Swagger / OpenAPI

## Author

**Abdul Vajeth**

Python Backend Developer | Django | Django REST Framework | MySQL

GitHub: https://github.com/abdulvajeth12

---

*This project was developed as a practical backend engineering portfolio project.*