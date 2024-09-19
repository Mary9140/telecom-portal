from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import boto3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # For session management

# Predefined agent data (email and hashed password)
agents = [
    {'id': 1, 'email': 'agent1@example.com', 'password': generate_password_hash('password1')},
    {'id': 2, 'email': 'agent2@example.com', 'password': generate_password_hash('password2')},
    {'id': 3, 'email': 'agent3@example.com', 'password': generate_password_hash('password3')},
    {'id': 4, 'email': 'agent4@example.com', 'password': generate_password_hash('password4')},
    {'id': 5, 'email': 'agent5@example.com', 'password': generate_password_hash('password5')}
]

# Database Connection (Amazon RDS MySQL)
connection = mysql.connector.connect(
    host='database-1.cz4s62km4gyi.us-east-1.rds.amazonaws.com',
    user='admin',
    password='marychitra9100',
    database='telecom'
)
cursor = connection.cursor(dictionary=True)

# AWS SNS Client Configuration
sns_client = boto3.client('sns', region_name='us-east-1')  # Adjust region as needed
sns_topic_arn = 'arn:aws:sns:us-east-1:296062580364:ticketraised'  # Replace with your SNS Topic ARN

# AWS SES Client Configuration (Removed as per request)
# ses_client = boto3.client('ses', region_name='us-east-1')  # Adjust region as needed
# sender_email = 'bmary202422@gmail.com'  # Replace with your verified SES sender email

# Home Page
@app.route('/')
def index():
    return render_template('index.html')

# Customer Registration
@app.route('/registration', methods=['GET', 'POST'])
def register_customer():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone_no = request.form['phone_no']
        address = request.form['address']

        # Hash password
        hashed_password = generate_password_hash(password)

        # Insert into customers table
        query = "INSERT INTO customers (name, email, password, phone_no, address) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query, (name, email, hashed_password, phone_no, address))
        connection.commit()

        return redirect('/login')
    return render_template('registration.html')

# Customer Login
@app.route('/login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Query customer from the database
        query = "SELECT * FROM customers WHERE email = %s"
        cursor.execute(query, (email,))
        customer = cursor.fetchone()

        if customer and check_password_hash(customer['password'], password):
            session['customer_id'] = customer['id']  # Store customer ID in session
            return redirect('/choose_option')
        else:
            return "Invalid credentials", 401
    return render_template('login.html')

# Agent Login
@app.route('/agent_login', methods=['GET', 'POST'])
def agent_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check agent credentials
        for agent in agents:
            if agent['email'] == email and check_password_hash(agent['password'], password):
                session['agent_id'] = agent['id']  # Store agent ID in session
                return redirect('/view_tickets')
        
        return "Invalid credentials", 401

    return render_template('agent_login.html')

# Choose Option (Customer)
@app.route('/choose_option')
def choose_option():
    if 'customer_id' not in session:
        return redirect('/login')

    return render_template('choose_option.html')

@app.route('/customer_dashboard')
def customer_dashboard():
    if 'customer_id' not in session:
        return redirect('/login')

    customer_id = session['customer_id']

    # Fetch customer details
    query = "SELECT * FROM customers WHERE id = %s"
    cursor.execute(query, (customer_id,))
    customer = cursor.fetchone()
    print(f"Customer Data: {customer}")

    # Fetch purchased services
    query = "SELECT service_name, purchase_date FROM purchases WHERE customer_id = %s"
    cursor.execute(query, (customer_id,))
    purchases = cursor.fetchall()
    print(f"Purchases Data: {purchases}")

    # Fetch raised tickets
    query = "SELECT description, plan_type, priority, status, date_raised FROM tickets WHERE customer_id = %s"
    cursor.execute(query, (customer_id,))
    tickets = cursor.fetchall()
    print(f"Tickets Data: {tickets}")

    return render_template('customer_dashboard.html', customer=customer, purchases=purchases, tickets=tickets)

# Buy a Service
@app.route('/buy_service', methods=['GET', 'POST'])
def buy_service():
    if 'customer_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        customer_id = session['customer_id']
        service_name = request.form['service_name']

        # Insert the purchased service into the database
        query = "INSERT INTO purchases (customer_id, service_name) VALUES (%s, %s)"
        cursor.execute(query, (customer_id, service_name))
        connection.commit()

        return "Service purchased successfully!", 200

    return render_template('buy_service.html')

# Raise a Ticket (Customer)
@app.route('/raise_ticket', methods=['GET', 'POST'])
def raise_ticket():
    if 'customer_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        customer_id = session['customer_id']
        description = request.form['description']
        priority = request.form['priority']

        # Insert the ticket into the tickets table
        query = "INSERT INTO tickets (customer_id, description, priority, status) VALUES (%s, %s, %s, 'Open')"
        cursor.execute(query, (customer_id, description, priority))
        connection.commit()

        # Send SNS notification
        subject = 'New Ticket Raised'
        message = f'A new ticket has been raised by customer ID {customer_id}. Description: {description}. Priority: {priority}.'
        sns_client.publish(
            TopicArn=sns_topic_arn,
            Message=message,
            Subject=subject
        )

        return "Ticket raised successfully!", 200

    return render_template('raise_ticket.html')

# View Tickets (Agent)
@app.route('/view_tickets')
def view_tickets():
    if 'agent_id' not in session:
        return redirect('/agent_login')

    # Fetch all open tickets
    query = "SELECT * FROM tickets WHERE status = 'Open'"
    cursor.execute(query)
    tickets = cursor.fetchall()

    return render_template('view_tickets.html', tickets=tickets)

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Run the Flask App
if __name__ == '__main__':
    app.run(debug=True)
