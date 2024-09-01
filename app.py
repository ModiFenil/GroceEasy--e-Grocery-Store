from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_pymongo import PyMongo
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

from werkzeug.security import generate_password_hash, check_password_hash
import razorpay
import datetime
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MongoDB Configuration
app.config['MONGO_URI'] = "mongodb+srv://fenilmodi088:fenil_modi@cluster0.oyzoc.mongodb.net/user_info?retryWrites=true&w=majority"
mongo = PyMongo(app)

# Razorpay Configuration
razorpay_client = razorpay.Client(auth=("rzp_test_tzfcc4gar0RCEo", "D96esAxWb5hEB6pdwz3zKc2G"))

# Logging Configuration
# logging.basicConfig(filename='app.log', level=logging.ERROR)

# Index Route (Redirects to home or signup)
@app.route('/', methods=['GET'])
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    else:
        return redirect(url_for('signup'))

# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'username' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        existing_user = mongo.db.users.find_one({'username': username})

        if existing_user is None:
            mongo.db.users.insert_one({'username': username, 'password': hashed_password})
            flash('You have successfully signed up! Please log in.')
            return redirect(url_for('login'))
        else:
            flash('User already exists! Please log in instead.')

    return render_template('signup.html')
# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = mongo.db.users.find_one({'username': username})

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            flash('Logged in successfully!')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials!')

    return render_template('login.html')

@app.before_request
def initialize_cart():
    if 'cart' not in session:
        session['cart'] = []

# Route to handle adding products to the cart
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product = request.json
    session['cart'].append(product)
    session.modified = True
    return jsonify({'success': True})

# Route to display the cart
@app.route('/cart')
def cart():
    if 'cart' in session:
        return render_template('cart.html', cart=session['cart'])
    else:
        flash('Your cart is empty!')
        return redirect(url_for('products'))

@app.route('/products')
def products():
    if 'username' not in session:
        flash('Please log in or sign up to view products!')
        return redirect(url_for('home'))
    return render_template('products.html')

@app.route('/user')
def user():
    if 'username' in session:
        return render_template('user.html', username=session['username'])
    else:
        flash('Please login first!')
        return redirect(url_for('login'))

# Home Route
@app.route('/home')
def home():
    if 'username' in session:
        orders = mongo.db.orders.find({'user': session['username']}).sort('order_date', -1)
        return render_template('home.html', username=session['username'], orders=orders)
    else:
        flash('Please log in or sign up to access product pages.')
        return redirect(url_for('signup'))

# Logout Route
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out!')
    return redirect(url_for('login'))

# Checkout Route
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        if 'username' in session:
            name = request.form['name']
            address = request.form['address']
            city = request.form['city']
            postal_code = request.form['postal_code']

            cart_total = sum(item['price'] for item in session['cart'])

            order = razorpay_client.order.create({
                'amount': cart_total * 100,
                'currency': 'INR',
                'payment_capture': '1'
            })

            session['order_id'] = order['id']
            session['delivery_info'] = {
                'name': name,
                'address': address,
                'city': city,
                'postal_code': postal_code
            }

            return jsonify({'success': True, 'order_id': order['id'], 'cart_total': cart_total})

        else:
            flash('Please login first!')
            return redirect(url_for('login'))

    cart_total = sum(item['price'] for item in session['cart'])
    return render_template('checkout.html', cart_total=cart_total)

@app.route('/purchase_history')
def purchase_history():
    if 'username' in session:
        username = session['username']
        orders = mongo.db.orders.find({'user': username}).sort('order_date', -1)
        return render_template('history.html', orders=orders)
    else:
        flash('Please login first!')
        return redirect(url_for('login'))

# Route to handle removing items from the cart
@app.route('/remove_item', methods=['POST'])
def remove_item():
    data = request.get_json()
    item_id = data.get('itemId')
    cart = session.get('cart', [])
    updated_cart = [item for item in cart if item['id'] != item_id]
    session['cart'] = updated_cart
    total = sum(item['price'] for item in updated_cart)
    return jsonify({'success': True, 'cart': updated_cart, 'total': total})

# Route to handle payment success
@app.route('/payment_success', methods=['POST'])
def payment_success():
    if 'order_id' in session:
        order_id = session['order_id']
        delivery_info = session['delivery_info']
        cart_items = session['cart']
        total_amount = sum(item['price'] for item in cart_items)
        mongo.db.orders.insert_one({
            'order_id': order_id,
            'user': session['username'],
            'delivery_info': delivery_info,
            'items': cart_items,
            'order_date': datetime.datetime.now(),
            'total_amount': total_amount
        })
        session.pop('cart', None)
        return render_template('payment_success.html', order_id=order_id, items=cart_items, total_amount=total_amount)

    return redirect(url_for('home'))

# Error Handlers
# @app.errorhandler(404)
# def not_found_error(error):
#     return render_template('404.html'), 404

# @app.errorhandler(500)
# def internal_error(error):
#     return render_template('500.html'), 500

# @app.errorhandler(TemplateNotFound)
# def template_not_found_error(error):
#     logging.error(f'Template not found: {error}')
#     return render_template('404.html'), 404

# @app.errorhandler(Exception)
# def handle_exception(error):
#     logging.error(f'Unhandled exception: {error}')
#     return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
