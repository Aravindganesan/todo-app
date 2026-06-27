# Activity Tracker Requirements Document

## 1. Business Requirements

The Activity Tracker is a lightweight Kanban-style task management application that allows users to create, organize, and track work items across three workflow stages:

- Backlog
- In Progress
- Completed

The application should support:
- creating a task with a title and username
- assigning the task to a workflow stage
- moving tasks between stages using drag-and-drop or action buttons
- viewing an audit trail of changes for each task
- viewing a shared activity history feed for all tasks
- deleting tasks when they are no longer needed


The current build reflects a simple internal workflow tool for tracking activities and their progression over time.

## 2. Technical Requirements

### Frontend Design Pattern
- The frontend is implemented as a single-page interface using plain HTML, CSS, and vanilla JavaScript.
- The UI uses a responsive three-column Kanban board layout.
- Each task card displays:
  - title
  - username
  - last updated timestamp
  - workflow action buttons
  - a per-task history panel
- The page also includes a global activity history section showing the latest changes across all tasks

### API Implementation
- The application uses Flask as the web framework.
- REST-style API endpoints are implemented for:
  - listing todos
  - creating todos
  - moving todos between workflow stages
  - viewing per-task history
  - viewing the full activity history feed
  - deleting todos
- The frontend communicates with the backend using fetch requests in JSON.

### Backend
- The backend is implemented in Python with Flask.
- The server runs locally and serves the HTML interface and API responses.
- The app is configured to use a PostgreSQL connection string via environment variable or default local connection.

### Database Choice
- PostgreSQL is used as the persistent database.
- The database schema includes:
  - workflow_steps reference table for normalized workflow states
  - todos table for task records
  - todo_history table for change tracking
- The workflow state is stored as a normalized reference and linked to each todo item.

## 3. Test Results

### Unit Testing
Unit testing was performed using Python's built-in unittest framework.

Test command executed:
```bash
python3 -m unittest discover -s tests -v
```

Results:
- 4 tests executed
- 4 tests passed
- 0 failures
- 0 errors

Covered scenarios:
- listing todos
- creating a todo and persisting it to the database
- moving a todo to a new workflow stage
- retrieving the history of a todo
- retrieving the shared activity history feed

### Issues Logged
No blocking issues were found during unit testing.
The current build is considered functionally stable for the implemented features.

### Verification Notes
The history endpoint was verified successfully through the Flask test client and returned recorded activity entries for tasks and workflow transitions.

### Run Instructions
```bash
cd /Users/aravindganesan/Documents/Code/todo-app
python3 app.py
```

The application is available locally at:
```text
http://127.0.0.1:5000
```

### Docker

Build the images and start the app with Postgres using Docker Compose:
```bash
# build and start (detached)
docker compose build
docker compose up -d

# view logs
docker compose logs -f web

# stop and remove
docker compose down
```

By default the compose stack creates a Postgres database using the credentials configured in `docker-compose.yml`. The web service is available at `http://127.0.0.1:5000` once the services start.
