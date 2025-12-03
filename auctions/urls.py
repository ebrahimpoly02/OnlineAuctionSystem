from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('create/', views.create_auction, name='create_auction'),
    path('auction/<int:auction_id>/', views.auction_detail, name='auction_detail'),
    path('auction/<int:auction_id>/bid/', views.place_bid, name='place_bid'),
    path('watchlist/', views.watchlist, name='watchlist'),
path('auction/<int:auction_id>/watchlist/add/', views.add_to_watchlist, name='add_to_watchlist'),
path('auction/<int:auction_id>/watchlist/remove/', views.remove_from_watchlist, name='remove_from_watchlist'),
path('auction/<int:auction_id>/buy-now/', views.buy_now, name='buy_now'),
path('auction/<int:auction_id>/buy-now/process/', views.process_buy_now, name='process_buy_now'),
path('account/', views.account, name='account'),
path('account/edit/', views.edit_account, name='edit_account'),
path('auction/<int:auction_id>/edit/', views.edit_listing, name='edit_listing'),
path('image/<int:image_id>/delete/', views.delete_image, name='delete_image'),
path('auction/<int:auction_id>/delete/', views.delete_listing, name='delete_listing'),
path('rate-seller/<int:payment_id>/', views.rate_seller, name='rate_seller'),
]