# FoodExpress - Food Delivery Web Application

A full-featured food delivery platform built with **Django (Python)**, **SQLite**,
and **HTML5 / CSS3 / JavaScript (Bootstrap 5)**.

Four roles are supported out of the box: **Customer**, **Restaurant**, **Delivery
Partner**, and **Administrator**.

---

## Features

**Customer**
- Register & Login, Browse & search restaurants/dishes, View menu
- Add to Cart, Place Orders, (simulated) Online Payment
- Live Order Tracking, Ratings & Reviews

**Restaurant**
- Manage Profile, Manage Food Menu (add/edit/delete items, categories)
- Accept / Reject Orders, Update Order Status, View Sales report

**Delivery Partner**
- View Assigned/Available Orders, Accept Delivery
- Update Delivery Status, View Earnings

**Administrator**
- Manage Users (block/unblock), Manage Restaurants (approve/reject)
- Manage Delivery Partners (approve), Manage Orders, Manage Categories
- Manage Coupons, View Reports (revenue, top restaurants, monthly trend)
- Full Django Admin panel at `/admin/` for direct database management

**Cross-cutting**
- Role-based authentication & authorization
- Shopping cart (single restaurant per cart)
- Coupons & discounts, GST + delivery fee calculation
- Email notifications on order placement/status change (console backend by default)
- Fully responsive UI (Bootstrap 5)

---

## Project Structure

```
foodapp/
├── manage.py
├── requirements.txt
├── db.sqlite3                # created after migrate
├── foodapp/                  # Django project (settings, urls, wsgi/asgi)
├── core/                     # Main app
│   ├── models.py             # Users, Restaurants, FoodItems, Cart, Orders, Payments, Reviews...
│   ├── views.py               # All view logic (customer / restaurant / delivery / admin)
│   ├── forms.py
│   ├── admin.py               # Django admin registrations
│   ├── urls.py
│   ├── decorators.py          # Role-based access control
│   ├── context_processors.py  # Cart badge count
│   ├── management/commands/seed_data.py   # Demo data seeder
│   ├── templates/             # All HTML templates (Bootstrap 5)
│   └── static/core/css/style.css
└── media/                     # Uploaded images (restaurant logos, food photos, etc.)
```

## Database Tables (Models)

| Table              | Purpose                                              |
|---------------------|-------------------------------------------------------|
| `User`              | Custom user model with `role` (Customer/Restaurant/Delivery/Admin) |
| `Restaurant`         | Restaurant profile, owned by a Restaurant-role user   |
| `FoodCategory`       | Global categories (Pizza, Chinese, Desserts, ...)     |
| `FoodItem`           | Menu items belonging to a restaurant                  |
| `Cart` / `CartItem`  | Customer's active shopping cart                       |
| `Coupon`             | Discount codes                                        |
| `DeliveryPartner`    | Delivery partner profile & availability                |
| `Order` / `OrderItem`| Placed orders and their line items                     |
| `Payment`            | Payment record per order (simulated gateway)           |
| `Review`             | Customer ratings & reviews per delivered order          |

---

## Setup Instructions

### 1. Requirements
- Python 3.10+ installed on your machine

### 2. Extract the project and create a virtual environment
```bash
cd foodapp
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply database migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create an admin (superuser) account
```bash
python manage.py createsuperuser
```
Log in with this account and it will automatically be treated as an Administrator
(superusers bypass the `role` check). You can also create a dedicated user with
`role = ADMIN` from the Django admin panel (`/admin/`) if you prefer a non-superuser
admin account.

### 6. (Optional but recommended) Seed demo data
Populates a few demo restaurants, menu items, categories, a delivery partner and a
coupon code so you have something to click around with immediately:
```bash
python manage.py seed_data
```
This creates:
- Restaurant owner logins: `pizza_owner`, `burger_owner`, `tiffin_owner` (password: `DemoPass123`)
- Delivery partner login: `delivery_demo` (password: `DemoPass123`)
- Coupon code: `WELCOME50` (50% off, up to Rs.100, minimum order Rs.200)

### 7. Run the development server
```bash
python manage.py runserver
```
Visit **http://127.0.0.1:8000/** in your browser.

- Customer/Restaurant/Delivery sign-up: `http://127.0.0.1:8000/accounts/register/`
- Login: `http://127.0.0.1:8000/accounts/login/`
- Django Admin: `http://127.0.0.1:8000/admin/`

---

## How the Order Flow Works

1. **Customer** browses restaurants → adds items to cart → checks out (enters
   address, picks a payment method, optionally applies a coupon).
2. On checkout, an `Order` + `Payment` are created (payment is simulated: any method
   except Cash on Delivery is marked `SUCCESS` immediately).
3. **Restaurant** sees the new order on their dashboard and can **Accept/Reject** it,
   then move it through **Preparing → Ready**.
4. When an order is marked **Ready**, it becomes visible to available, approved
   **Delivery Partners**, who can accept it, then mark **Out for Delivery** and
   finally **Delivered**.
5. Once **Delivered**, the customer can leave a **Rating & Review** for the
   restaurant from their Orders page.
6. Throughout the flow, email notifications are sent (visible in your terminal
   console, since the project uses Django's console email backend by default —
   swap `EMAIL_BACKEND` in `foodapp/settings.py` for a real SMTP backend in
   production).

---

## Notes on "Online Payment"

There's no real payment gateway wired in (no live keys required to run this
project). At checkout, a `Payment` record is created and instantly marked as
`SUCCESS` for all non-COD methods, simulating a successful transaction — this
keeps the project self-contained and runnable offline. To integrate a real
gateway (Razorpay/Stripe/PayPal), replace the payment-creation block in
`core/views.checkout()` with a call to your gateway's API/SDK.

## Switching to a Production Email Backend

In `foodapp/settings.py`, replace:
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```
with your SMTP settings, e.g.:
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

## Security Notes Before Deploying

- Change `SECRET_KEY` in `foodapp/settings.py`
- Set `DEBUG = False` and configure `ALLOWED_HOSTS`
- Move secrets (SECRET_KEY, email credentials) into environment variables
- Consider PostgreSQL/MySQL for production instead of SQLite
- Serve static/media files via a proper web server or cloud storage (S3, etc.)

---

## Tech Stack Summary

| Layer      | Technology                          |
|------------|--------------------------------------|
| Frontend   | HTML5, CSS3, JavaScript, Bootstrap 5 |
| Backend    | Python, Django                       |
| Database   | SQLite                               |
| Auth       | Django's built-in auth + custom role-based `User` model |

Enjoy building on top of FoodExpress!
