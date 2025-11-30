from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User, Auction, AuctionImage, Category
from .forms import AuctionForm
from django.utils import timezone
from datetime import timedelta, datetime, time
from django.db.models import Q

# Homepage with search and filters
def index(request):
    # Get search query and filters from GET parameters
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    # Start with all active auctions
    auctions = Auction.objects.filter(status='active')
    
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
    
    # Get all images for this auction
    images = auction.images.all().order_by('-is_primary', 'uploaded_at')
    
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
    
    # Get bid count and highest bid
    bids = auction.bids.all().order_by('-bid_amount')
    bid_count = bids.count()
    highest_bid = bids.first() if bids.exists() else None
    
    context = {
        'auction': auction,
        'images': images,
        'bid_count': bid_count,
        'highest_bid': highest_bid,
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
    
    # Get bid amount
    try:
        bid_amount = float(request.POST.get('bid_amount', 0))
    except ValueError:
        messages.error(request, 'Invalid bid amount.')
        return redirect('auction_detail', auction_id=auction_id)
    
    # Calculate minimum required bid
    minimum_bid = auction.current_price + auction.minimum_bid_increment
    
    # Validate bid amount
    if bid_amount < minimum_bid:
        messages.error(request, f'Your bid must be at least {minimum_bid:.2f} BHD (current price + minimum increment).')
        return redirect('auction_detail', auction_id=auction_id)
    
    # Create the bid
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