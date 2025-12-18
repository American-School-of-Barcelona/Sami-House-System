# House Points System - Flask Web Application

A simple web interface for the House Points System using Flask (Python) with basic HTML and no JavaScript.

## Features

- 🏆 **View Winning House** - See which house is currently winning with detailed stats
- 📊 **Leaderboard** - Complete standings with points, wins, and placements
- 👥 **Student Management** - View all students and add new ones
- 📅 **Event Management** - View events and add new events with results
- 🎯 **No JavaScript** - Pure HTML forms with Flask backend

## Project Structure

```
Sami-House-System/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── playground/
│   ├── testhouse.db               # SQLite database
│   ├── database_insert_guide.py   # Database operations class
│   └── analysis_queries.py        # Query analysis class
└── templates/                      # HTML templates
    ├── base.html                  # Base template with navigation
    ├── index.html                 # Home page (winning house & standings)
    ├── winning_house.html         # Detailed winning house page
    ├── leaderboard.html           # Full leaderboard
    ├── students.html              # All students list
    ├── add_student.html           # Add student form
    ├── events.html                # All events list
    ├── event_details.html         # Event details page
    └── add_event.html             # Add event form
```

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install Flask directly:
```bash
pip install Flask
```

### 2. Ensure Database Exists

Make sure `playground/testhouse.db` exists and has data. If not, create it using:

```bash
cd playground
sqlite3 testhouse.db < sample_schema.sql
sqlite3 testhouse.db < testdata.sql
```

### 3. Run the Application

```bash
python app.py
```

The app will start on `http://localhost:5000`

### 4. Open in Browser

Visit: `http://localhost:5000`

## Pages & Routes

### Main Pages

| Route | Description |
|-------|-------------|
| `/` | Home page with current winner and standings |
| `/winning-house` | Detailed page about the winning house |
| `/leaderboard` | Complete leaderboard with all students by standing |
| `/students` | List of all students |
| `/add-student` | Form to add a new student |
| `/events` | List of all events |
| `/event/<id>` | Details of a specific event |
| `/add-event` | Form to add a new event with results |

## Using the Application

### Adding a Student

1. Click "Add Student" in the navigation
2. Fill in:
   - First Name
   - Last Name
   - Email
   - House (select from dropdown)
   - Class Year (select from dropdown)
3. Click "Add Student"
4. You'll be redirected to the students list

### Adding an Event

1. Click "Add Event" in the navigation
2. Fill in event information:
   - Event Date
   - Event Description (e.g., "Winter House Challenge")
   - Event Type (Sports, Academic, Arts, Other)
3. Fill in results for each house:
   - Points Earned (e.g., 400 for 1st place)
   - Rank (1-4)
   - Leave blank if house didn't participate
4. Click "Add Event"
5. Event will be added with all results

### Viewing Data

- **Home Page**: Quick overview of winner and standings
- **Winning House**: Detailed breakdown of winning house with all students
- **Leaderboard**: Full standings with placement counts
- **Students**: Browse all students by house
- **Events**: See all past events and their results

## How It Works

### Flask Application (`app.py`)

The Flask app:
1. Connects to the SQLite database
2. Uses the `HousePointsAnalyzer` class for queries
3. Uses the `HousePointsDatabase` class for inserts
4. Renders HTML templates with data
5. Handles form submissions (POST requests)

### Database Operations

**Queries** (Read Data):
```python
analyzer = HousePointsAnalyzer(DB_PATH)
winner = analyzer.get_winning_house()
```

**Inserts** (Add Data):
```python
db = HousePointsDatabase(DB_PATH)
db.add_student('John', 'Doe', 'jdoe@email.com', house_id=1, class_year_id=2)
```

### HTML Templates

All templates extend `base.html` which includes:
- Navigation bar
- Styling (CSS)
- Flash message display
- Common layout

Forms use standard HTML with `method="POST"`:
```html
<form method="POST" action="{{ url_for('add_student') }}">
    <input type="text" name="fname" required>
    <button type="submit">Add Student</button>
</form>
```

## Customization

### Change House Colors

Edit the CSS in `templates/base.html`:

```css
.house-yellow { background: #f4c430; }
.house-blue { background: #4169e1; }
.house-green { background: #228b22; }
.house-red { background: #dc143c; }
```

### Change Port

Edit `app.py`:

```python
app.run(debug=True, host='0.0.0.0', port=8080)  # Change 5000 to 8080
```

### Add New Pages

1. Add a route in `app.py`:
```python
@app.route('/my-page')
def my_page():
    # Get data
    data = analyzer.some_query()
    return render_template('my_page.html', data=data)
```

2. Create template `templates/my_page.html`:
```html
{% extends "base.html" %}
{% block content %}
    <!-- Your HTML here -->
{% endblock %}
```

## Troubleshooting

### "Database not found" error
- Make sure `playground/testhouse.db` exists
- Check the `DB_PATH` in `app.py`

### "Module not found" error
- Run `pip install Flask`
- Make sure you're in the correct directory

### "Address already in use" error
- Another app is using port 5000
- Change the port in `app.py` or stop the other app

### Changes not showing
- Flask debug mode auto-reloads, but try:
  - Refresh browser (Ctrl+R or Cmd+R)
  - Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
  - Restart Flask (`Ctrl+C` then `python app.py`)

## Production Deployment

For production, use a proper WSGI server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Or use Flask's built-in server with production config:
```python
app.run(debug=False, host='0.0.0.0', port=5000)
```

## Technologies Used

- **Flask** - Python web framework
- **SQLite3** - Database
- **Jinja2** - Template engine (included with Flask)
- **HTML5** - Markup
- **CSS3** - Styling
- **No JavaScript** - Pure server-side rendering

## License

Educational project for IB CS coursework.
