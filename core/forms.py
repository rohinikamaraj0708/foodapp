from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import (User, Restaurant, FoodItem, FoodCategory, Review,
                      DeliveryPartner, Coupon)


class BootstrapFormMixin:
    """Adds Bootstrap CSS classes to every field's widget automatically."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')


class CustomerSignUpForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)
    address = forms.CharField(max_length=255, required=False, widget=forms.Textarea(attrs={'rows': 2}))

    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'address', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CUSTOMER
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data.get('phone', '')
        user.address = self.cleaned_data.get('address', '')
        if commit:
            user.save()
        return user


class RestaurantSignUpForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)
    restaurant_name = forms.CharField(max_length=150)
    restaurant_address = forms.CharField(max_length=255, widget=forms.Textarea(attrs={'rows': 2}))

    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.RESTAURANT
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data.get('phone', '')
        if commit:
            user.save()
            Restaurant.objects.create(
                owner=user,
                name=self.cleaned_data['restaurant_name'],
                address=self.cleaned_data['restaurant_address'],
                phone=self.cleaned_data.get('phone', ''),
            )
        return user


class DeliverySignUpForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)
    vehicle_type = forms.CharField(max_length=50, required=False)
    vehicle_number = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.DELIVERY
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data.get('phone', '')
        if commit:
            user.save()
            DeliveryPartner.objects.create(
                user=user,
                vehicle_type=self.cleaned_data.get('vehicle_type', ''),
                vehicle_number=self.cleaned_data.get('vehicle_number', ''),
            )
        return user


class UserProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'address', 'profile_image')


class RestaurantProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ('name', 'description', 'address', 'city', 'phone', 'logo',
                   'opening_time', 'closing_time', 'is_open')
        widgets = {
            'opening_time': forms.TimeInput(attrs={'type': 'time'}),
            'closing_time': forms.TimeInput(attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class FoodItemForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = FoodItem
        fields = ('name', 'category', 'description', 'price', 'image', 'is_veg', 'is_available')
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = FoodCategory.objects.filter(is_active=True)


class ReviewForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Review
        fields = ('rating', 'comment')
        widgets = {
            'rating': forms.Select(choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Share your experience...'}),
        }


class CheckoutForm(BootstrapFormMixin, forms.Form):
    delivery_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}))
    payment_method = forms.ChoiceField(choices=[
        ('CARD', 'Credit / Debit Card'),
        ('UPI', 'UPI'),
        ('NETBANKING', 'Net Banking'),
        ('WALLET', 'Wallet'),
        ('COD', 'Cash on Delivery'),
    ])
    coupon_code = forms.CharField(max_length=30, required=False)


class CouponForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Coupon
        fields = '__all__'
        widgets = {
            'valid_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
