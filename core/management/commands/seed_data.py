from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (User, Restaurant, FoodCategory, FoodItem, Coupon, DeliveryPartner)


class Command(BaseCommand):
    help = 'Seeds the database with demo categories, restaurants, menu items, a coupon and a delivery partner.'

    def handle(self, *args, **options):
        categories = ['Pizza', 'Burgers', 'Chinese', 'South Indian', 'North Indian', 'Desserts', 'Beverages']
        cat_objs = {}
        for name in categories:
            cat, _ = FoodCategory.objects.get_or_create(name=name)
            cat_objs[name] = cat
        self.stdout.write(self.style.SUCCESS(f'Created/verified {len(categories)} categories.'))

        demo_restaurants = [
            {
                'username': 'pizza_owner', 'restaurant': 'Pizza Palace', 'city': 'Madurai',
                'items': [
                    ('Margherita Pizza', 'Pizza', 249, True),
                    ('Farmhouse Pizza', 'Pizza', 299, True),
                    ('Chicken Pepperoni Pizza', 'Pizza', 349, False),
                    ('Garlic Bread', 'Pizza', 129, True),
                ],
            },
            {
                'username': 'burger_owner', 'restaurant': 'Burger Barn', 'city': 'Madurai',
                'items': [
                    ('Classic Veg Burger', 'Burgers', 99, True),
                    ('Cheese Burst Burger', 'Burgers', 149, True),
                    ('Grilled Chicken Burger', 'Burgers', 179, False),
                    ('Crispy Fries', 'Burgers', 79, True),
                ],
            },
            {
                'username': 'tiffin_owner', 'restaurant': 'South Spice Tiffin Center', 'city': 'Madurai',
                'items': [
                    ('Masala Dosa', 'South Indian', 89, True),
                    ('Idli Sambar (4 pcs)', 'South Indian', 69, True),
                    ('Chicken Chettinad', 'North Indian', 259, False),
                    ('Filter Coffee', 'Beverages', 39, True),
                ],
            },
        ]

        for entry in demo_restaurants:
            user, created = User.objects.get_or_create(
                username=entry['username'],
                defaults={'role': User.Role.RESTAURANT, 'email': f"{entry['username']}@example.com"}
            )
            if created:
                user.set_password('DemoPass123')
                user.save()

            restaurant, _ = Restaurant.objects.get_or_create(
                owner=user,
                defaults={
                    'name': entry['restaurant'],
                    'address': f"{entry['restaurant']}, Main Road",
                    'city': entry['city'],
                    'is_approved': True,
                    'is_open': True,
                }
            )
            if not restaurant.is_approved:
                restaurant.is_approved = True
                restaurant.save()

            for item_name, cat_name, price, is_veg in entry['items']:
                FoodItem.objects.get_or_create(
                    restaurant=restaurant,
                    name=item_name,
                    defaults={
                        'category': cat_objs.get(cat_name),
                        'price': price,
                        'is_veg': is_veg,
                        'description': f'Delicious {item_name} made fresh to order.',
                    }
                )
            self.stdout.write(self.style.SUCCESS(f'Seeded restaurant: {restaurant.name}'))

        delivery_user, created = User.objects.get_or_create(
            username='delivery_demo',
            defaults={'role': User.Role.DELIVERY, 'email': 'delivery_demo@example.com'}
        )
        if created:
            delivery_user.set_password('DemoPass123')
            delivery_user.save()
        DeliveryPartner.objects.get_or_create(
            user=delivery_user,
            defaults={'vehicle_type': 'Bike', 'vehicle_number': 'TN-59-AB-1234', 'is_approved': True}
        )
        self.stdout.write(self.style.SUCCESS('Seeded demo delivery partner: delivery_demo / DemoPass123'))

        Coupon.objects.get_or_create(
            code='WELCOME50',
            defaults={
                'discount_percent': 50,
                'max_discount_amount': 100,
                'minimum_order_amount': 200,
                'valid_from': timezone.now(),
                'valid_to': timezone.now() + timedelta(days=90),
                'is_active': True,
            }
        )
        self.stdout.write(self.style.SUCCESS('Seeded demo coupon: WELCOME50 (50% off, up to Rs.100, min order Rs.200)'))

        self.stdout.write(self.style.SUCCESS(
            '\nDemo restaurant owner logins (password: DemoPass123): '
            'pizza_owner, burger_owner, tiffin_owner'
        ))
        self.stdout.write(self.style.SUCCESS('Seeding complete!'))
