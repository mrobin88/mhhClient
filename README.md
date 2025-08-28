# Mission Hiring Hall Client System

A client intake and case management system for Mission Hiring Hall, serving San Francisco's Mission District.

## Features

- **Client Intake Form** - Online registration with resume upload
- **Case Notes System** - Track client interactions and progress
- **Admin Dashboard** - Full Django admin interface
- **Staff Dashboard** - Search and manage clients

## Quick Start

```bash
# Start development servers
./start-dev.sh

# Access the system
# Frontend: http://localhost:5176
# Backend: http://localhost:8000
# Admin: http://localhost:8000/admin (admin/admin)
```

## Tech Stack

- **Backend**: Django 3.2 + Django REST Framework
- **Frontend**: Vue.js 3 + Tailwind CSS
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **File Storage**: Local (dev) / Azure Blob (prod)

## Environment

Copy `env.example` to `env.local` and configure your settings.

