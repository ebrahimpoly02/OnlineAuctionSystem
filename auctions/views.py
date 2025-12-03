from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User, Auction, AuctionImage, Category
from .forms import AuctionForm
from django.utils import timezone
from datetime import timedelta, datetime, time
from django.db.models import Q
from .models import Payment
from django.db.models import Sum

# Homepage with search and filters
def index(request):
    # Get search query and filters from GET parameters
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    # Start with all active auctions that haven't ended
    now = timezone.now()
    auctions = Auction.objects.filter(status='active', end_time__gt=now)
    
    # Apply search filter
    if search_query:
        auctions = auctions.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Apply category filter
    if category_filter:
        auctions = auctions.filter(category_id=category_filter)
    
    # Apply sorting
    if sort_by == 'price_low':
        auctions = auctions.order_by('current_price')
    elif sort_by == 'price_high':
        auctions = auctions.order_by('-current_price')
    elif sort_by == 'ending_soon':
        auctions = auctions.order_by('end_time')
    else:  # default: newest first
        auctions = auctions.order_by('-created_at')
    
    auctions = auctions[:50]  # Limit to 50 results
    
    # Add bid count and time remaining for each auction
    for auction in auctions:
        auction.bid_count = auction.bids.count()
        
        # Calculate time remaining
        now = timezone.now()
        if auction.end_time > now:
            time_diff = auction.end_time - now
            days = time_diff.days
            hours = time_diff.seconds // 3600
            minutes = (time_diff.seconds % 3600) // 60
            
            if days > 0:
                auction.time_remaining = f"{days} days {hours} hours"
            elif hours > 0:
                auction.time_remaining = f"{hours} hours {minutes} minutes"
            else:
                auction.time_remaining = f"{minutes} minutes"
        else:
            auction.time_remaining = "Ended"
    
    # Get all categories for filter dropdown
    categories = Category.objects.all()
    
    context = {
        'auctions': auctions,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'sort_by': sort_by,
    }
    return render(request, 'auctions/index.html', context)

# User Registration
def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        is_seller = request.POST.get('is_seller') == 'on'
        phone_digits = request.POST.get('phone', '').strip()
        phone = f"973{phone_digits}" if phone_digits else ''
        
        # Validation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return redirect('register')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return redirect('register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return redirect('register')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_seller=is_seller
        )
        user.phone = phone
        user.save()
        messages.success(request, 'Account created successfully! Please login.')
        return redirect('login')
    
    return render(request, 'auctions/register.html')

# User Login
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {username}!')
            return redirect('index')
        else:
            messages.error(request, 'Invalid username or password!')
            return redirect('login')
    
    return render(request, 'auctions/login.html')

# User Logout
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully!')
    return redirect('index')

@login_required
def create_auction(request):
    # Check if user is a seller
    if not request.user.is_seller:
        messages.error(request, "Only sellers can create auctions.")
        return redirect('index')
    
    if request.method == 'POST':
        form = AuctionForm(request.POST, request.FILES)
        if form.is_valid():
            auction = form.save(commit=False)
            auction.seller = request.user
            auction.current_price = auction.starting_price
            
            # Combine date and time fields into end_time
            end_date = form.cleaned_data['end_date']
            hour = int(form.cleaned_data['end_time_hour'])
            minute = int(form.cleaned_data['end_time_minute'])
            period = form.cleaned_data['end_time_period']
            
            # Convert to 24-hour format
            if period == 'PM' and hour != 12:
                hour += 12
            elif period == 'AM' and hour == 12:
                hour = 0
            
            end_time_obj = time(hour=hour, minute=minute)
            auction.end_time = datetime.combine(end_date, end_time_obj)
            
            # Make timezone aware
            auction.end_time = timezone.make_aware(auction.end_time)
            
            auction.save()
            
            # Handle multiple images
            images = request.FILES.getlist('images')
            if images:
                for i, image in enumerate(images[:5]):  # Limit to 5 images
                    AuctionImage.objects.create(
                        auction=auction,
                        image=image,
                        is_primary=(i == 0)  # First image is primary
                    )
            
            messages.success(request, "Auction created successfully!")
            return redirect('index')
    else:
        form = AuctionForm()
    
    return render(request, 'auctions/create_auction.html', {'form': form})

def auction_detail(request, auction_id):
    """Display detailed information about a specific auction"""
    try:
        auction = Auction.objects.get(id=auction_id)
    except Auction.DoesNotExist:
        messages.error(request, 'Auction not found.')
        return redirect('index')
    
    # get all images for this auction
    images = auction.images.all().order_by('-is_primary', 'uploaded_at')
    
    # calculate time remaining
    now = timezone.now()
    if auction.end_time > now:
        time_diff = auction.end_time - now
        days = time_diff.days
        hours = time_diff.seconds // 3600
        minutes = (time_diff.seconds % 3600) // 60
        
        if days > 0:
            auction.time_remaining = f"{days} days {hours} hours"
        elif hours > 0:
            auction.time_remaining = f"{hours} hours {minutes} minutes"
        else:
            auction.time_remaining = f"{minutes} minutes"
    else:
        auction.time_remaining = "Ended"
    
    # get all bids ordered by most recent first
    bids = auction.bids.all().order_by('-bid_time')
    bid_count = bids.count()
    highest_bid = bids.first() if bids.exists() else None
    
    # check if auction is in user's watchlist
    in_watchlist = False
    if request.user.is_authenticated:
        from .models import Watchlist
        in_watchlist = Watchlist.objects.filter(user=request.user, auction=auction).exists()
    
    # Check if auction has ended and determine winner
    auction_ended = auction.end_time <= timezone.now()
    is_winner = False
    winner_username = None
    
    if auction_ended and highest_bid:
        winner_username = highest_bid.bidder.username
        if request.user.is_authenticated:
            is_winner = (highest_bid.bidder == request.user)
    
    # Calculate seller rating
    from .models import Rating
    from django.db.models import Avg, Count
    seller_ratings = Rating.objects.filter(rated_user=auction.seller).aggregate(
        avg_rating=Avg('rating_score'),
        total_ratings=Count('id')
    )
    
    context = {
        'auction': auction,
        'images': images,
        'bid_count': bid_count,
        'highest_bid': highest_bid,
        'bids': bids,
        'in_watchlist': in_watchlist,
        'auction_ended': auction_ended,
        'is_winner': is_winner,
        'winner_username': winner_username,
        'seller_avg_rating': seller_ratings['avg_rating'],
        'seller_total_ratings': seller_ratings['total_ratings'],
    }
    return render(request, 'auctions/auction_detail.html', context)
    
@login_required
def place_bid(request, auction_id):
    """Handle bid placement"""
    if request.method != 'POST':
        return redirect('auction_detail', auction_id=auction_id)
    
    try:
        auction = Auction.objects.get(id=auction_id)
    except Auction.DoesNotExist:
        messages.error(request, 'Auction not found.')
        return redirect('index')
    
    # Validation checks
    if auction.seller == request.user:
        messages.error(request, 'You cannot bid on your own auction.')
        return redirect('auction_detail', auction_id=auction_id)
    
    if auction.status != 'active':
        messages.error(request, 'This auction is not active.')
        return redirect('auction_detail', auction_id=auction_id)
    
    if auction.end_time <= timezone.now():
        messages.error(request, 'This auction has ended.')
        return redirect('auction_detail', auction_id=auction_id)
    
    # get bid amount
    try:
        bid_amount = float(request.POST.get('bid_amount', 0))
    except ValueError:
        messages.error(request, 'Invalid bid amount.')
        return redirect('auction_detail', auction_id=auction_id)
    
    # calculate minimum required bid
    minimum_bid = auction.current_price + auction.minimum_bid_increment
    
    # validate bid amount
    if bid_amount < minimum_bid:
        messages.error(request, f'Your bid must be at least {minimum_bid:.2f} BHD (current price + minimum increment).')
        return redirect('auction_detail', auction_id=auction_id)
    
    # create the bid
    from .models import Bid
    Bid.objects.create(
        auction=auction,
        bidder=request.user,
        bid_amount=bid_amount
    )
    
    # Update auction current price
    auction.current_price = bid_amount
    auction.save()
    
    messages.success(request, f'Your bid of {bid_amount:.2f} BHD has been placed successfully!')
    return redirect('auction_detail', auction_id=auction_id)

@login_required
def add_to_watchlist(request, auction_id):
    """Add auction to user's watchlist"""
    try:
        auction = Auction.objects.get(id=auction_id)
    except Auction.DoesNotExist:
        messages.error(request, 'Auction not found.')
        return redirect('index')
    
    from .models import Watchlist
    
    # Check if already in watchlist
    if Watchlist.objects.filter(user=request.user, auction=auction).exists():
        messages.info(request, 'This auction is already in your watchlist.')
    else:
        Watchlist.objects.create(user=request.user, auction=auction)
        messages.success(request, 'Auction added to your watchlist!')
    
    return redirect('auction_detail', auction_id=auction_id)

@login_required
def remove_from_watchlist(request, auction_id):
    """Remove auction from user's watchlist"""
    try:
        auction = Auction.objects.get(id=auction_id)
    except Auction.DoesNotExist:
        messages.error(request, 'Auction not found.')
        return redirect('index')
    
    from .models import Watchlist
    
    watchlist_item = Watchlist.objects.filter(user=request.user, auction=auction).first()
    if watchlist_item:
        watchlist_item.delete()
        messages.success(request, 'Auction removed from your watchlist.')
    else:
        messages.info(request, 'This auction is not in your watchlist.')
    
    return redirect('auction_detail', auction_id=auction_id)

@login_required
def watchlist(request):
    """Display user's watchlist"""
    from .models import Watchlist
    
    watchlist_items = Watchlist.objects.filter(user=request.user).select_related('auction')
    
    # add bid count and time remaining for each auction
    auctions = []
    for item in watchlist_items:
        auction = item.auction
        auction.bid_count = auction.bids.count()
        
        # calculate time remaining
        now = timezone.now()
        if auction.end_time > now:
            time_diff = auction.end_time - now
            days = time_diff.days
            hours = time_diff.seconds // 3600
            minutes = (time_diff.seconds % 3600) // 60
            
            if days > 0:
                auction.time_remaining = f"{days} days {hours} hours"
            elif hours > 0:
                auction.time_remaining = f"{hours} hours {minutes} minutes"
            else:
                auction.time_remaining = f"{minutes} minutes"
        else:
            auction.time_remaining = "Ended"
        
        auctions.append(auction)
    
    context = {
        'auctions': auctions,
        'watchlist_count': len(auctions)
    }
    return render(request, 'auctions/watchlist.html', context)

@login_required
def buy_now(request, auction_id):
    """Handle Buy Now purchase or payment for won auction"""
    try:
        auction = Auction.objects.get(id=auction_id)
    except Auction.DoesNotExist:
        messages.error(request, 'Auction not found.')
        return redirect('index')
    
    # Validation checks
    if auction.seller == request.user:
        messages.error(request, 'You cannot buy your own auction.')
        return redirect('auction_detail', auction_id=auction_id)
    
    # Check if this is a Buy Now purchase or payment for won auction
    is_buy_now = auction.buy_now_price and auction.status == 'active' and auction.end_time > timezone.now()
    
    # Check if user won the auction
    is_winner = False
    if auction.end_time <= timezone.now():
        highest_bid = auction.bids.order_by('-bid_amount').first()
        is_winner = (highest_bid and highest_bid.bidder == request.user)
    
    # Allow payment if it's Buy Now OR if user won the auction
    if not is_buy_now and not is_winner:
        if auction.end_time <= timezone.now():
            messages.error(request, 'This auction has ended and you did not win.')
        elif not auction.buy_now_price:
            messages.error(request, 'Buy Now is not available for this auction.')
        else:
            messages.error(request, 'This auction is not available for purchase.')
        return redirect('auction_detail', auction_id=auction_id)
    
    # Get all images for display
    images = auction.images.all().order_by('-is_primary', 'uploaded_at')
    
    # Determine the payment amount
    payment_amount = auction.buy_now_price if is_buy_now else auction.current_price
    
    context = {
        'auction': auction,
        'images': images,
        'buy_now_price': payment_amount,
        'is_won_auction': is_winner,
    }
    return render(request, 'auctions/buy_now.html', context)

@login_required
def process_buy_now(request, auction_id):
    """Process Buy Now payment or payment for won auction"""
    if request.method != 'POST':
        return redirect('buy_now', auction_id=auction_id)
    
    try:
        auction = Auction.objects.get(id=auction_id)
    except Auction.DoesNotExist:
        messages.error(request, 'Auction not found.')
        return redirect('index')
    
    # validation
    if auction.seller == request.user:
        messages.error(request, 'You cannot buy your own auction.')
        return redirect('auction_detail', auction_id=auction_id)
    
    # Check if this is a Buy Now purchase or payment for won auction
    is_buy_now = auction.buy_now_price and auction.status == 'active' and auction.end_time > timezone.now()
    
    # Check if user won the auction
    is_winner = False
    if auction.end_time <= timezone.now():
        highest_bid = auction.bids.order_by('-bid_amount').first()
        is_winner = (highest_bid and highest_bid.bidder == request.user)
    
    # Validate that payment is allowed
    if not is_buy_now and not is_winner:
        messages.error(request, 'You are not authorized to pay for this auction.')
        return redirect('auction_detail', auction_id=auction_id)
    
    # get form data
    card_number = request.POST.get('card_number', '').replace(' ', '')
    card_name = request.POST.get('card_name', '')
    expiry_month = request.POST.get('expiry_month', '')
    expiry_year = request.POST.get('expiry_year', '')
    cvv = request.POST.get('cvv', '')
    billing_address = request.POST.get('billing_address', '')
    city = request.POST.get('city', '')
    postal_code = request.POST.get('postal_code', '')
    
    # validation
    errors = []
    
    # card number validation must be 16 digits
    if not card_number.isdigit() or len(card_number) != 16:
        errors.append('Card number must be 16 digits.')
    
    # card name validation
    if not card_name or len(card_name.strip()) < 3:
        errors.append('Cardholder name is required.')
    
    # expiry validation
    try:
        exp_month = int(expiry_month)
        exp_year = int(expiry_year)
        current_year = timezone.now().year
        current_month = timezone.now().month
        
        if exp_month < 1 or exp_month > 12:
            errors.append('Invalid expiry month.')
        elif exp_year < current_year or (exp_year == current_year and exp_month < current_month):
            errors.append('Card has expired.')
    except ValueError:
        errors.append('Invalid expiry date.')
    
    # CVV validation must be 3 digits
    if not cvv.isdigit() or len(cvv) != 3:
        errors.append('CVV must be 3 digits.')
    
    # billing address validation
    if not billing_address or not city:
        errors.append('Billing address and city are required.')
    
    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect('buy_now', auction_id=auction_id)
    
    # Determine payment amount
    payment_amount = auction.buy_now_price if is_buy_now else auction.current_price
    
    # Check if already paid
    from .models import Payment
    already_paid = Payment.objects.filter(
        auction=auction,
        buyer=request.user,
        status='completed'
    ).exists()
    
    if already_paid:
        messages.error(request, 'You have already paid for this auction.')
        return redirect('auction_detail', auction_id=auction_id)
    
    # If all validations passed, process payment 
    Payment.objects.create(
        auction=auction,
        buyer=request.user,
        seller=auction.seller,
        amount=payment_amount,
        payment_method=f"Card ending in {card_number[-4:]}",
        status='completed'
    )
    
    # update auction status
    auction.status = 'sold'
    auction.save()
    
    messages.success(request, f'Purchase successful! You bought {auction.title} for {payment_amount} BHD.')
    return redirect('auction_detail', auction_id=auction_id)
@login_required
def account(request):
    """Display user account page with tabs"""
    # Get user's bids
    user_bids = request.user.bids_placed.all().select_related('auction').order_by('-bid_time')
    
    # Categorize bids
    active_bids = []
    won_auctions = []
    lost_auctions = []
    
    for bid in user_bids:
        auction = bid.auction
        
        # Check if user has highest bid
        highest_bid = auction.bids.order_by('-bid_amount').first()
        is_winning = (highest_bid and highest_bid.bidder == request.user)
        
        # Check auction status
        if auction.status == 'active' and auction.end_time > timezone.now():
            # Active auction
            bid.status = 'Winning' if is_winning else 'Outbid'
            bid.status_class = 'winning' if is_winning else 'outbid'
            active_bids.append(bid)
        elif auction.end_time <= timezone.now() or auction.status != 'active':
            # Ended auction
            if is_winning:
                # Check if user already paid for this auction
                from .models import Payment
                already_paid = Payment.objects.filter(
                    auction=auction,
                    buyer=request.user,
                    status='completed'
                ).exists()
                
                # Show in Won Auctions regardless of payment status
                if already_paid:
                    bid.status = 'Won - Paid'
                    bid.status_class = 'won paid'
                    bid.already_paid = True
                else:
                    bid.status = 'Won'
                    bid.status_class = 'won'
                    bid.already_paid = False
                
                won_auctions.append(bid)
            else:
                bid.status = 'Lost'
                bid.status_class = 'lost'
                lost_auctions.append(bid)
    
    # Get user's listings (if seller)
    my_listings = []
    if request.user.is_seller:
        my_listings = Auction.objects.filter(seller=request.user).order_by('-created_at')
        
        # Add bid count and actual status for each listing
        for listing in my_listings:
            listing.bid_count = listing.bids.count()
            
            # Determine actual status based on time
            if listing.status == 'sold':
                listing.display_status = 'Sold'
            elif listing.end_time <= timezone.now():
                listing.display_status = 'Ended'
            else:
                listing.display_status = 'Active'
    
    # Get order history (Buy Now purchases and won auctions paid)
    from .models import Payment, Rating
    order_history = Payment.objects.filter(buyer=request.user, status='completed').order_by('-transaction_date')

# Check if each order has been rated
    for order in order_history:
     order.has_rating = Rating.objects.filter(
        rater_user=request.user,
        rated_user=order.seller,
        auction=order.auction
    ).exists()
    
    context = {
        'active_bids': active_bids,
        'won_auctions': won_auctions,
        'lost_auctions': lost_auctions,
        'my_listings': my_listings,
        'order_history': order_history,
    }
    return render(request, 'auctions/account.html', context)
@login_required
def edit_account(request):
    """Edit user account details"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        phone_digits = request.POST.get('phone', '').strip()
        phone = f"973{phone_digits}" if phone_digits else ''
        
        errors = []
        
        # Validate username (if changed)
        if username != request.user.username:
            if not username:
                errors.append('Username cannot be empty.')
            elif User.objects.filter(username=username).exists():
                errors.append('Username already taken.')
            else:
                request.user.username = username
        
        # Validate email (if changed)
        if email != request.user.email:
            if not email:
                errors.append('Email cannot be empty.')
            elif User.objects.filter(email=email).exists():
                errors.append('Email already registered.')
            else:
                request.user.email = email
        
        # Update phone (optional field, always allow changes)
        request.user.phone = phone
        
        # Validate password change (if requested)
        if new_password:
            if not current_password:
                errors.append('Current password is required to change password.')
            elif not request.user.check_password(current_password):
                errors.append('Current password is incorrect.')
            elif len(new_password) < 8:
                errors.append('New password must be at least 8 characters.')
            elif new_password != confirm_password:
                errors.append('New passwords do not match.')
            else:
                request.user.set_password(new_password)
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('edit_account')
        
        # Save changes
        request.user.save()
        
        # If password was changed, update session
        if new_password:
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
        
        messages.success(request, 'Account updated successfully!')
        return redirect('account')
    
    return render(request, 'auctions/edit_account.html')

@login_required
def edit_listing(request, auction_id):
    """Edit auction listing (seller only, no bids allowed)"""
    try:
        auction = Auction.objects.get(id=auction_id)
    except Auction.DoesNotExist:
        messages.error(request, 'Auction not found.')
        return redirect('account')
    
    # Check if user is the seller
    if auction.seller != request.user:
        messages.error(request, 'You can only edit your own auctions.')
        return redirect('account')
    
    # Check if auction has ended or sold
    if auction.end_time <= timezone.now():
        messages.error(request, 'Cannot edit ended auction.')
        return redirect('auction_detail', auction_id=auction_id)

    if auction.status == 'sold':
        messages.error(request, 'Cannot edit sold auction.')
        return redirect('auction_detail', auction_id=auction_id)
    
    if request.method == 'POST':
        # Get form data
        auction.title = request.POST.get('title', '').strip()
        auction.description = request.POST.get('description', '').strip()
        auction.category_id = request.POST.get('category')
        auction.condition = request.POST.get('condition')
        auction.location = request.POST.get('location')
        auction.shipping_method = request.POST.get('shipping_method')
        
        # Check again if auction has bids (for price editing)
        has_bids = auction.bids.exists()

        # Prices
        try:
            if not has_bids:
                auction.starting_price = float(request.POST.get('starting_price', 0))
                auction.current_price = auction.starting_price  # Reset if no bids

            auction.minimum_bid_increment = float(request.POST.get('minimum_bid_increment', 1))

            buy_now_price = request.POST.get('buy_now_price', '').strip()
            auction.buy_now_price = float(buy_now_price) if buy_now_price else None

            if auction.shipping_method == 'shipping':
                auction.shipping_cost = float(request.POST.get('shipping_cost', 0))
            else:
                auction.shipping_cost = None

        except ValueError:
            messages.error(request, 'Invalid price values.')
            return redirect('edit_listing', auction_id=auction_id)

        # Validation
        if not auction.title or not auction.description:
            messages.error(request, 'Title and description are required.')
            return redirect('edit_listing', auction_id=auction_id)
        
        if auction.starting_price <= 0:
            messages.error(request, 'Starting price must be greater than 0.')
            return redirect('edit_listing', auction_id=auction_id)
        
        # Save auction
        auction.save()
        
        # Save additional new images
        new_images = request.FILES.getlist('new_images')
        for img in new_images[:5]:
            AuctionImage.objects.create(
                auction=auction,
                image=img,
                is_primary=False
            )
        
        messages.success(request, 'Auction updated successfully!')
        return redirect('auction_detail', auction_id=auction_id)

    # GET request show edit form
    categories = Category.objects.all()
    images = auction.images.all()

    context = {
        'auction': auction,
        'categories': categories,
        'images': images,
    }
    return render(request, 'auctions/edit_listing.html', context)


@login_required
def delete_image(request, image_id):
    """Delete auction image"""
    try:
        image = AuctionImage.objects.get(id=image_id)
    except AuctionImage.DoesNotExist:
        messages.error(request, 'Image not found.')
        return redirect('account')
    
    auction = image.auction
    
    # Check if user is the seller
    if auction.seller != request.user:
        messages.error(request, 'You can only delete images from your own auctions.')
        return redirect('account')
    
    # Check if auction has bids
    has_bids = auction.bids.exists()
    
    # Delete image
    image.delete()
    messages.success(request, 'Image deleted successfully.')
    return redirect('edit_listing', auction_id=auction.id)

@login_required
def delete_listing(request, auction_id):
    """Delete auction listing (only if no bids)"""
    try:
        auction = Auction.objects.get(id=auction_id)
    except Auction.DoesNotExist:
        messages.error(request, 'Auction not found.')
        return redirect('account')
    
    # Check if user is the seller
    if auction.seller != request.user:
        messages.error(request, 'You can only delete your own auctions.')
        return redirect('account')
    
    # Check if auction has bids
    if auction.bids.exists():
        messages.error(request, 'Cannot delete auction that has bids.')
        return redirect('account')
    
    # Delete the auction (images will cascade delete automatically)
    auction_title = auction.title
    auction.delete()
    
    messages.success(request, f'Auction "{auction_title}" has been deleted successfully.')
    return redirect('account')
@login_required
def rate_seller(request, payment_id):
    """Rate seller after completed transaction"""
    try:
        payment = Payment.objects.get(id=payment_id, buyer=request.user, status='completed')
    except Payment.DoesNotExist:
        messages.error(request, 'Payment not found.')
        return redirect('account')
    
    # Check if already rated
    from .models import Rating
    already_rated = Rating.objects.filter(
        rater_user=request.user,
        rated_user=payment.seller,
        auction=payment.auction
    ).exists()
    
    if already_rated:
        messages.info(request, 'You have already rated this seller.')
        return redirect('account')
    
    if request.method == 'POST':
        rating_score = request.POST.get('rating_score')
        comment = request.POST.get('comment', '').strip()
        
        # Validation
        try:
            rating_score = int(rating_score)
            if rating_score < 1 or rating_score > 5:
                messages.error(request, 'Rating must be between 1 and 5.')
                return redirect('rate_seller', payment_id=payment_id)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid rating.')
            return redirect('rate_seller', payment_id=payment_id)
        
        # Create rating
        Rating.objects.create(
            rater_user=request.user,
            rated_user=payment.seller,
            auction=payment.auction,
            rating_score=rating_score,
            comment=comment
        )
        
        messages.success(request, 'Thank you for rating the seller!')
        return redirect('account')
    
    context = {
        'payment': payment,
        'auction': payment.auction,
        'seller': payment.seller,
    }
    return render(request, 'auctions/rate_seller.html', context)

@login_required
def admin_dashboard(request):
    """Admin dashboard - only accessible to admin users"""
    # Check if user is admin
    if not request.user.is_admin:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('index')
    
    # Get statistics
    from .models import Payment
    from django.db.models import Sum
    from django.utils import timezone
    
    total_users = User.objects.count()
    total_sellers = User.objects.filter(is_seller=True).count()
    total_auctions = Auction.objects.count()
    now = timezone.now()
    active_auctions = Auction.objects.filter(status='active', end_time__gt=now).count()
    total_transactions = Payment.objects.filter(status='completed').count()
    total_revenue = Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0
    
    # Get all users (for management)
    all_users = User.objects.all().order_by('-date_joined')
    
    # Get all auctions (for moderation)
    all_auctions = Auction.objects.all().order_by('-created_at')[:50]  # Limit to 50 most recent
    
    # Add actual status for each auction
    for auction in all_auctions:
        if auction.status == 'sold':
            auction.actual_status = 'Sold'
        elif auction.end_time <= now:
            auction.actual_status = 'Ended'
        else:
            auction.actual_status = 'Active'
    
    context = {
        'total_users': total_users,
        'total_sellers': total_sellers,
        'total_auctions': total_auctions,
        'active_auctions': active_auctions,
        'total_transactions': total_transactions,
        'total_revenue': total_revenue,
        'all_users': all_users,
        'all_auctions': all_auctions,
    }
    return render(request, 'auctions/admin_dashboard.html', context)

@login_required
def admin_ban_user(request, user_id):
    """Ban/unban user"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('index')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('admin_dashboard')
    
    # Don't allow banning admins
    if user.is_admin:
        messages.error(request, 'Cannot ban admin users.')
        return redirect('admin_dashboard')
    
    # Toggle active status
    user.is_active = not user.is_active
    user.save()
    
    status = "banned" if not user.is_active else "unbanned"
    messages.success(request, f'User {user.username} has been {status}.')
    return redirect('admin_dashboard')

@login_required
def admin_delete_auction(request, auction_id):
    """Delete inappropriate auction"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('index')
    
    try:
        auction = Auction.objects.get(id=auction_id)
    except Auction.DoesNotExist:
        messages.error(request, 'Auction not found.')
        return redirect('admin_dashboard')
    
    auction_title = auction.title
    auction.delete()
    
    messages.success(request, f'Auction "{auction_title}" has been deleted.')
    return redirect('admin_dashboard')