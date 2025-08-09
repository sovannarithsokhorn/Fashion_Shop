# admin_dashboard/models.py
from django.db import models
from django.db.models import Sum

# --- CHOICES FOR ENUM-LIKE FIELDS ---
GENDER_CHOICES = [
    ('M', 'Men'),
    ('W', 'Women'),
    ('U', 'Unisex'),
    ('K', 'Kids'),
]

ADDRESS_TYPE_CHOICES = [
    ('S', 'Shipping'),
    ('B', 'Billing'),
]

ORDER_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('PROCESSING', 'Processing'),
    ('SHIPPED', 'Shipped'),
    ('DELIVERED', 'Delivered'),
    ('CANCELLED', 'Cancelled'),
]

PAYMENT_STATUS_CHOICES = [
    ('PAID', 'Paid'),
    ('PENDING', 'Pending'),
    ('REFUNDED', 'Refunded'),
    ('FAILED', 'Failed'),
]

DISCOUNT_TYPE_CHOICES = [
    ('PERCENTAGE', 'Percentage'),
    ('FIXED_AMOUNT', 'Fixed Amount'),
    ('FREE_SHIPPING', 'Free Shipping'),
]

# --- APP MANAGEMENT MODELS ---

class Member(models.Model):
    """
    Represents a member who creates/manages the application. This model is
    standalone and not linked to Django's built-in User model. It stores
    information about the app administrators or creators.
    """
    member_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='member_profiles/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Member"
        verbose_name_plural = "Members"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def profile_picture_url(self):
        """
        Returns the URL of the profile picture, or a default image if none is set.
        """
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        # Provide a path to a default image if no profile picture is uploaded
        return "/static/images/default_member_profile.png"

# --- E-COMMERCE MODELS ---

class Brand(models.Model):
    brand_id = models.AutoField(primary_key=True)
    brand_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    website_url = models.URLField(max_length=200, blank=True, null=True)

    class Meta:
        verbose_name = "Brand"
        verbose_name_plural = "Brands"
        ordering = ['brand_name']

    def __str__(self):
        return self.brand_name

class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100, unique=True)
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories'
    )
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['category_name']

    def __str__(self):
        return self.category_name

class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, related_name='products')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    material = models.CharField(max_length=100, blank=True, null=True)
    care_instructions = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['-created_at', 'product_name']

    def __str__(self):
        return self.product_name

    @property
    def total_stock(self):
        """Calculates the total quantity in stock across all variants of this product."""
        return self.variants.aggregate(total_quantity=Sum('quantity_in_stock'))['total_quantity'] or 0


class ProductVariant(models.Model):
    variant_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    color = models.CharField(max_length=50)
    size = models.CharField(max_length=50)
    sku = models.CharField(max_length=100, unique=True, help_text="Stock Keeping Unit")
    quantity_in_stock = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"
        unique_together = ('product', 'color', 'size')
        ordering = ['product__product_name', 'color', 'size']

    def __str__(self):
        return f"{self.product.product_name} - {self.color} - {self.size} ({self.sku})"

class ProductImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='images',
        help_text="Optional: Link image to a specific variant if it's variant-specific"
    )
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    is_thumbnail = models.BooleanField(default=False, help_text="Designates if this is the primary thumbnail image for the product/variant.")
    display_order = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ['product__product_name', 'display_order']

    def __str__(self):
        return f"Image for {self.product.product_name} (Order: {self.display_order})"

    @property
    def image_url(self):
        """Returns the URL of the product image, or a default image if none is set."""
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        # Provide a path to a default image if no product image is uploaded
        return "/static/images/default_product.png"


class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    password_hash = models.CharField(max_length=255, help_text="Hashed password for security")
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='customer_profiles/', null=True, blank=True)
    notes = models.TextField(blank=True, null=True, help_text="Internal notes about the customer")

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ['-registration_date']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def profile_picture_url(self):
        """Returns the URL of the customer's profile picture, or a default image if none is set."""
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        # Provide a path to a default image if no profile picture is uploaded
        return "/static/images/default_profile.png"


class Address(models.Model):
    address_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses')
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    address_type = models.CharField(max_length=1, choices=ADDRESS_TYPE_CHOICES)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"
        ordering = ['customer__email', 'address_type']

    def __str__(self):
        return f"{self.customer.email} - {self.address_line1}, {self.city}"

class Order(models.Model):
    order_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.ForeignKey(
        Address,
        on_delete=models.CASCADE,
        null=True,
        related_name='shipping_orders',
        help_text="Address used for shipping this order"
    )
    billing_address = models.ForeignKey(
        Address,
        on_delete=models.CASCADE,
        null=True,
        related_name='billing_orders',
        help_text="Address used for billing this order"
    )
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    shipping_method = models.CharField(max_length=100, blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-order_date']

    def __str__(self):
        # Corrected f-string for Order __str__
        return f"Order #{self.order_id} by {self.customer.email if self.customer else 'Guest'}"

class OrderItem(models.Model):
    order_item_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, related_name='order_items')
    quantity = models.IntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price of the item at the time of purchase")

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        unique_together = ('order', 'variant')
        ordering = ['order__order_id']

    def __str__(self):
        return f"{self.quantity} x {self.variant.product.product_name} ({self.variant.sku}) in Order #{self.order.order_id}"

class Cart(models.Model):
    cart_id = models.AutoField(primary_key=True)
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, null=True, blank=True, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shopping Cart"
        verbose_name_plural = "Shopping Carts"
        ordering = ['-updated_at']

    def __str__(self):
        return f"Cart for {self.customer.email if self.customer else 'Guest'}"

class CartItem(models.Model):
    cart_item_id = models.AutoField(primary_key=True)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        unique_together = ('cart', 'variant')
        ordering = ['cart__cart_id', 'added_at']

    def __str__(self):
        return f"{self.quantity} x {self.variant.product.product_name} ({self.variant.sku}) in Cart #{self.cart.cart_id}"

class Review(models.Model):
    review_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, related_name='reviews')
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], help_text="Rating from 1 to 5 stars")
    review_text = models.TextField(blank=True, null=True)
    review_date = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False, help_text="Whether the review has been approved by an admin")

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        unique_together = ('product', 'customer')
        ordering = ['-review_date']

    def __str__(self):
        return f"Review for {self.product.product_name} by {self.customer.email if self.customer else 'Anonymous'} - {self.rating} stars"

class Promotion(models.Model):
    promotion_id = models.AutoField(primary_key=True)
    promo_code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    usage_limit = models.IntegerField(blank=True, null=True, help_text="Total number of times this promo can be used")
    per_customer_limit = models.IntegerField(blank=True, null=True, help_text="Number of times a single customer can use this promo")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.promo_code} ({self.discount_type}: {self.discount_value})"

class AppliedPromotion(models.Model):
    applied_promo_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='applied_promotions')
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='applied_to_orders')
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2, help_text="The actual discount amount applied to the order")
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Applied Promotion"
        verbose_name_plural = "Applied Promotions"
        unique_together = ('order', 'promotion')
        ordering = ['order__order_id', '-applied_at']

    def __str__(self):
        return f"Order #{self.order.order_id} - {self.promotion.promo_code} (-${self.discount_applied})"

class Wishlist(models.Model):
    wishlist_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='wishlists')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='wishlists')
    added_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Wishlist Item"
        verbose_name_plural = "Wishlist Items"
        unique_together = ('customer', 'variant')
        ordering = ['customer__email', '-added_date']

    def __str__(self):
        # Corrected f-string syntax for Wishlist __str__
        return f"{self.customer.email}'s Wishlist: {self.variant.product.product_name} ({self.variant.sku})"
