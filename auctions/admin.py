from django.contrib import admin
from .models import User, Category, Auction, Bid, Payment, Rating, Watchlist

admin.site.register(User)
admin.site.register(Category)
admin.site.register(Auction)
admin.site.register(Bid)
admin.site.register(Payment)
admin.site.register(Rating)
admin.site.register(Watchlist)