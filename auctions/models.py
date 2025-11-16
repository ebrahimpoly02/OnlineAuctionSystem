from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# Custom User Model
class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_seller = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.username

# Categories Table
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

# Auctions Table
class Auction(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('sold', 'Sold'),
        ('cancelled', 'Cancelled'),
    ]
    
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auctions_created')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    starting_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    buy_now_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image_url = models.CharField(max_length=500, blank=True, null=True)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

# Bids Table
class Bid(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='bids')
    bidder = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bids_placed')
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    bid_time = models.DateTimeField(auto_now_add=True)
    is_winning_bid = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-bid_time']
    
    def __str__(self):
        return f"{self.bidder.username} - {self.bid_amount} BHD on {self.auction.title}"

# Payments Table
class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('disputed', 'Disputed'),
    ]
    
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_made')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_received')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    def __str__(self):
        return f"Payment {self.id} - {self.amount} BHD - {self.status}"

# Ratings Table
class Rating(models.Model):
    rated_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings_received')
    rater_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings_given')
    auction = models.ForeignKey(Auction, on_delete=models.SET_NULL, null=True, blank=True)
    rating_score = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating_score__gte=1) & models.Q(rating_score__lte=5),
                name='rating_score_range'
            )
        ]
    
    def __str__(self):
        return f"{self.rater_user.username} rated {self.rated_user.username} - {self.rating_score}/5"

# Watchlist Table
class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlist')
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'auction')
    
    def __str__(self):
        return f"{self.user.username} watching {self.auction.title}"