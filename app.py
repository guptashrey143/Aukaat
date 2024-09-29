from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
# from instance.models import db, FinancialData  # Adjust the import based on your project structure

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(60), nullable=False)

    @property
    def is_active(self):
        return True

class FinancialData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    salary = db.Column(db.Float, nullable=False)
    monthly_rent = db.Column(db.Float, nullable=False)
    monthly_expense = db.Column(db.Float, nullable=False)
    monthly_investment = db.Column(db.Float, nullable=False)
    monthly_savings = db.Column(db.Float, nullable=False)

    user = db.relationship('User', backref=db.backref('financial_data', lazy=True))

    __table_args__ = (db.UniqueConstraint('user_id', 'year', 'month', name='unique_user_month_year'),)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        ssn = request.form['ssn']
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        # salary = request.form['salary']
        # monthly_rent = request.form['monthly_rent']
        # monthly_expense = request.form['monthly_expense']
        # monthly_investment = request.form['monthly_investment']
        # monthly_savings = request.form['monthly_savings']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = current_user.id
    data = FinancialData.query.filter_by(user_id=user_id).all()

    if not data:
        return render_template('dashboard.html', graphJSON=None, message="No financial data available.")

    total_income = sum(d.salary for d in data)
    total_expenses = sum(d.monthly_expense for d in data)
    total_investment = sum(d.monthly_investment for d in data)
    total_savings = sum(d.monthly_savings for d in data)

    labels = ['Expenses', 'Investment', 'Savings']
    values = [total_expenses, total_investment, total_savings]

    # Create pie chart
    pie_fig = px.pie(values=values, names=labels, title='Income Distribution')
    pie_fig.update_layout(width=500, height=500)
    graphJSON = pie_fig.to_json()

    return render_template('dashboard.html', total_income=total_income, total_expenses=total_expenses, total_investment=total_investment, total_savings=total_savings, graphJSON=graphJSON)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


from datetime import datetime, timedelta

@app.route('/visualize', methods=['GET', 'POST'])
@login_required
def visualize():
    user_id = current_user.id

    if request.method == 'POST':
        selected_year = int(request.form.get('year'))
        selected_month = int(request.form.get('month'))
    else:
        # Fetch the last available month and year
        last_data = FinancialData.query.filter_by(user_id=user_id).order_by(FinancialData.year.desc(), FinancialData.month.desc()).first()
        if not last_data:
            return render_template('visualize.html', message="No financial data available.")
        selected_year = last_data.year
        selected_month = last_data.month

    # Fetch data for the selected month
    selected_month_data = FinancialData.query.filter_by(user_id=user_id, year=selected_year, month=selected_month).all()

    # Fetch data for the selected year
    year_data = FinancialData.query.filter_by(user_id=user_id, year=selected_year).all()

    # Fetch all data for calculating averages
    all_data = FinancialData.query.filter_by(user_id=user_id).all()

    # Calculate totals for the selected month
    total_income_selected_month = sum(d.salary for d in selected_month_data)
    total_expenses_selected_month = sum(d.monthly_expense for d in selected_month_data)
    total_investment_selected_month = sum(d.monthly_investment for d in selected_month_data)
    total_savings_selected_month = sum(d.monthly_savings for d in selected_month_data)
    total_rent_selected_month = sum(d.monthly_rent for d in selected_month_data)

    # Calculate totals for the selected year
    total_income_year = sum(d.salary for d in year_data)
    total_expenses_year = sum(d.monthly_expense for d in year_data)
    total_investment_year = sum(d.monthly_investment for d in year_data)
    total_savings_year = sum(d.monthly_savings for d in year_data)
    total_rent_year = sum(d.monthly_rent for d in year_data)

    # Calculate averages for the selected year (dividing by the number of unique years)
    num_years = len(set(d.year for d in all_data))
    avg_expenses_year = total_expenses_year / num_years if num_years else 0
    avg_investment_year = total_investment_year / num_years if num_years else 0
    avg_savings_year = total_savings_year / num_years if num_years else 0
    avg_rent_year = total_rent_year / num_years if num_years else 0

    # Calculate overall averages for all data (dividing by the number of unique months)
    num_months = len(set((d.year, d.month) for d in all_data))
    total_expenses_all = sum(d.monthly_expense for d in all_data)
    total_investment_all = sum(d.monthly_investment for d in all_data)
    total_savings_all = sum(d.monthly_savings for d in all_data)
    total_rent_all = sum(d.monthly_rent for d in all_data)

    avg_expenses_all = total_expenses_all / num_months if num_months else 0
    avg_investment_all = total_investment_all / num_months if num_months else 0
    avg_savings_all = total_savings_all / num_months if num_months else 0
    avg_rent_all = total_rent_all / num_months if num_months else 0

    # Create pie chart for the selected month
    labels = ['Expenses', 'Investment', 'Savings', 'Rent']
    values_selected_month = [total_expenses_selected_month, total_investment_selected_month, total_savings_selected_month, total_rent_selected_month]
    pie_fig_selected_month = px.pie(values=values_selected_month, names=labels, title='Income Distribution for Selected Month')
    pie_fig_selected_month.update_layout(width=500, height=500)
    selected_month_graphJSON = pie_fig_selected_month.to_json()

    # Create pie chart for the selected year
    values_year = [total_expenses_year, total_investment_year, total_savings_year, total_rent_year]
    pie_fig_year = px.pie(values=values_year, names=labels, title='Income Distribution for Selected Year')
    pie_fig_year.update_layout(width=500, height=500)
    year_graphJSON = pie_fig_year.to_json()

    # Create histogram for the selected month
    hist_fig_selected_month = go.Figure()
    hist_fig_selected_month.add_trace(go.Bar(x=labels, y=[total_expenses_selected_month, total_investment_selected_month, total_savings_selected_month, total_rent_selected_month], name='Selected Month'))
    hist_fig_selected_month.add_trace(go.Bar(x=labels, y=[avg_expenses_all, avg_investment_all, avg_savings_all, avg_rent_all], name='Average Month'))
    hist_fig_selected_month.update_layout(barmode='group', title='Comparison for Selected Month', width=500, height=500)
    selected_month_histJSON = hist_fig_selected_month.to_json()

    # Create histogram for the selected year
    hist_fig_year = go.Figure()
    hist_fig_year.add_trace(go.Bar(x=labels, y=[total_expenses_year, total_investment_year, total_savings_year, total_rent_year], name='Selected Year'))
    hist_fig_year.add_trace(go.Bar(x=labels, y=[avg_expenses_year, avg_investment_year, avg_savings_year, avg_rent_year], name='Average Year'))
    hist_fig_year.update_layout(barmode='group', title='Comparison for Selected Year', width=500, height=500)
    year_histJSON = hist_fig_year.to_json()

    return render_template('visualize.html', 
                           total_income_selected_month=total_income_selected_month, 
                           total_expenses_selected_month=total_expenses_selected_month, 
                           total_investment_selected_month=total_investment_selected_month, 
                           total_savings_selected_month=total_savings_selected_month, 
                           total_rent_selected_month=total_rent_selected_month,
                           selected_month_graphJSON=selected_month_graphJSON,
                           selected_month_histJSON=selected_month_histJSON,
                           total_income_year=total_income_year, 
                           total_expenses_year=total_expenses_year, 
                           total_investment_year=total_investment_year, 
                           total_savings_year=total_savings_year, 
                           total_rent_year=total_rent_year,
                           avg_expenses_year=avg_expenses_year,
                           avg_investment_year=avg_investment_year,
                           avg_savings_year=avg_savings_year,
                           avg_rent_year=avg_rent_year,
                           year_graphJSON=year_graphJSON,
                           year_histJSON=year_histJSON,
                           selected_year=selected_year,
                           selected_month=selected_month)



@app.route('/financial_data', methods=['GET', 'POST'])
@login_required
def financial_data():
    if request.method == 'POST':
        year = int(request.form['year'])
        month = int(request.form['month'])
        salary = request.form['salary']
        monthly_rent = request.form['monthly_rent']
        monthly_expense = request.form['monthly_expense']
        monthly_investment = request.form['monthly_investment']
        monthly_savings = request.form['monthly_savings']
        
        new_data = FinancialData(
            user_id=current_user.id,
            year=year,
            month=month,
            salary=salary,
            monthly_rent=monthly_rent,
            monthly_expense=monthly_expense,
            monthly_investment=monthly_investment,
            monthly_savings=monthly_savings
        )
        db.session.add(new_data)
        db.session.commit()
        return redirect(url_for('view_financial_data'))
    return render_template('financial_data.html')

@app.route('/view_financial_data')
@login_required
def view_financial_data():
    data = FinancialData.query.filter_by(user_id=current_user.id).all()
    return render_template('view_financial_data.html', data=data)

@app.route('/helpful-links')
@login_required
def helpful_links():
    links = [
        {"title": "What Is Finance?", "url": "https://www.investopedia.com/terms/f/finance.asp"},
        {"title": "The Basics of Investing In Stocks", "url": "https://dfi.wa.gov/financial-education/information/basics-investing-stocks"},
        {"title": "Exchange-Traded Fund (ETF): How to Invest and What It Is", "url": "https://www.investopedia.com/terms/e/etf.asp"},
        {"title": "What is cryptocurrency and how does it work?", "url": "https://usa.kaspersky.com/resource-center/definitions/what-is-cryptocurrency"},
        {"title": "How to Invest Money in 2024", "url": "https://www.nerdwallet.com/article/investing/how-to-invest-money"},
        {"title": "Budgeting 101: How to Create a Budget", "url": "https://www.nerdwallet.com/article/finance/how-to-budget"},
        {"title": "What Is a Savings Account?", "url": "https://www.investopedia.com/terms/s/savingsaccount.asp"},
        {"title": "What Is Credit and Why Is It Important?", "url": "https://www.experian.com/blogs/ask-experian/credit-education/what-is-credit/"},
        {"title": "Understanding Taxes: A Beginner's Guide", "url": "https://www.investopedia.com/taxes/tax-guide-for-beginners/"},
        {"title": "What Is Compound Interest?", "url": "https://www.investopedia.com/terms/c/compoundinterest.asp"}
    ]
    return render_template('helpful_links.html', links=links)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)