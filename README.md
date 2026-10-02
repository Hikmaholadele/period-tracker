# Period Tracker

A web-based period tracking application built with HTML, CSS, Python, Flask, and SQLite.

The application allows users to record their menstrual cycles, view their cycle history, and see estimated information about their upcoming cycle.

> **Note:** Cycle and fertility dates shown by this application are estimates for tracking purposes and should not be treated as medical advice or as a reliable method of contraception.

## Features

### Current Features

* Period tracking
* Cycle day display
* Estimated next period
* Estimated ovulation date
* Estimated fertile window
* Period history
* Responsive user interface

### Planned Features

* User registration and login
* Secure password storage
* Symptom tracking
* Calendar view
* Edit and delete period records
* Cycle statistics
* Charts and visualizations
* Mobile-friendly interface

## Technologies Used

### Frontend

* HTML5
* CSS3
* JavaScript

### Backend

* Python
* Flask

### Database

* SQLite

## Project Structure

```text
period-tracker/
│
├── app.py
├── database.db
├── requirements.txt
├── README.md
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── log_period.html
│   └── history.html
│
└── static/
    ├── css/
    │   └── style.css
    │
    └── js/
        └── script.js
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/period-tracker.git
```

### 2. Navigate to the project directory

```bash
cd period-tracker
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

### 4. Activate the virtual environment

#### Windows

```bash
venv\Scripts\activate
```

#### macOS/Linux

```bash
source venv/bin/activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

## Running the Application

Start the Flask development server:

```bash
python app.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

## How It Works

The user provides information such as:

* Period start date
* Period length
* Average cycle length

The application uses this information to calculate estimates such as:

```text
Period start date
       |
       v
Current cycle day
       |
       v
Estimated next period
       |
       v
Estimated ovulation
       |
       v
Estimated fertile window
```

These calculations are intended for personal tracking and are not medical predictions.

## Database

The application uses SQLite to store user and cycle information.

### Users

```text
id
name
email
password
created_at
```

### Periods

```text
id
user_id
start_date
end_date
cycle_length
period_length
created_at
```

### Symptoms

```text
id
user_id
period_id
symptom
severity
date
```

## Privacy and Security

Period and symptom information can be sensitive personal data.

The application should:

* Hash passwords instead of storing them as plain text
* Ensure users can only access their own records
* Validate submitted data
* Protect authenticated routes
* Use secure sessions
* Use HTTPS when deployed
* Avoid collecting unnecessary personal information

## Project Status

This project is currently under development.

### Development Roadmap

* [x] Create project structure
* [x] Create initial Flask application
* [x] Create dashboard template
* [ ] Style dashboard
* [ ] Create registration page
* [ ] Create login page
* [ ] Set up SQLite database
* [ ] Add user authentication
* [ ] Add period logging
* [ ] Add cycle calculations
* [ ] Add period history
* [ ] Add symptom tracking
* [ ] Add calendar
* [ ] Add charts
* [ ] Test application
* [ ] Deploy application

## Learning Objectives

This project is being developed to practice:

* HTML
* CSS
* JavaScript
* Python
* Flask
* SQLite
* SQL
* CRUD operations
* Authentication
* Backend development
* Frontend and backend communication
* Date and time calculations

## Disclaimer

This application is designed for educational and personal tracking purposes.

Period, ovulation, and fertile-window dates are estimates and can vary between individuals and between cycles. The application does not provide medical diagnosis, treatment, or guaranteed fertility information.

For medical questions or concerns about your menstrual cycle, consult a qualified healthcare professional.

## License

This project is currently intended for educational purposes.
