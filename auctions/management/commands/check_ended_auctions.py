from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMessage
from auctions.models import Auction, Bid

class Command(BaseCommand):
    help = 'Check and process ended auctions'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        
        # Find auctions that have ended but are still marked as active
        ended_auctions = Auction.objects.filter(
            status='active',
            end_time__lte=now
        )
        
        for auction in ended_auctions:
            # Get highest bid
            highest_bid = auction.bids.order_by('-bid_amount').first()
            
            if highest_bid:
                # Auction has bids - mark as sold
                auction.status = 'sold'
                auction.save()
                
                winner = highest_bid.bidder
                
                # Send congratulations email to WINNER
                try:
                    winner_subject = f'Congratulations! You Won: {auction.title}'
                    winner_message = f"""
Hi {winner.username},

🎉 Congratulations! You have won the auction for "{auction.title}"!

Final Winning Bid: {highest_bid.bid_amount} BHD
Auction Ended: {auction.end_time.strftime('%B %d, %Y at %I:%M %p')}
Seller: {auction.seller.username}

Please proceed to payment to complete your purchase.

Best regards,
Bidfinity Team
                    """
                    
                    winner_email = EmailMessage(
                        winner_subject,
                        winner_message,
                        to=[winner.email]
                    )
                    winner_email.send()
                    self.stdout.write(self.style.SUCCESS(f'✓ Winner email sent for auction: {auction.title}'))
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ Failed to send winner email: {str(e)}'))
                
                # Send notification email to SELLER
                try:
                    seller_subject = f'Your Auction Ended: {auction.title}'
                    seller_message = f"""
Hi {auction.seller.username},

Your auction for "{auction.title}" has ended!

Final Sale Price: {highest_bid.bid_amount} BHD
Winner: {winner.username}
Ended: {auction.end_time.strftime('%B %d, %Y at %I:%M %p')}

The buyer will proceed with payment shortly.

Best regards,
Bidfinity Team
                    """
                    
                    seller_email = EmailMessage(
                        seller_subject,
                        seller_message,
                        to=[auction.seller.email]
                    )
                    seller_email.send()
                    self.stdout.write(self.style.SUCCESS(f'✓ Seller email sent for auction: {auction.title}'))
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ Failed to send seller email: {str(e)}'))
                
            else:
                # No bids - mark as ended
                auction.status = 'ended'
                auction.save()
                
                # Notify seller that auction ended with no bids
                try:
                    seller_subject = f'Auction Ended (No Bids): {auction.title}'
                    seller_message = f"""
Hi {auction.seller.username},

Your auction for "{auction.title}" has ended without any bids.

Ended: {auction.end_time.strftime('%B %d, %Y at %I:%M %p')}

You can create a new listing with adjusted pricing or duration if you'd like to try again.

Best regards,
Bidfinity Team
                    """
                    
                    seller_email = EmailMessage(
                        seller_subject,
                        seller_message,
                        to=[auction.seller.email]
                    )
                    seller_email.send()
                    self.stdout.write(self.style.SUCCESS(f'✓ No-bid notification sent for: {auction.title}'))
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ Failed to send no-bid email: {str(e)}'))
        
        total_processed = ended_auctions.count()
        if total_processed > 0:
            self.stdout.write(self.style.SUCCESS(f'✓ Processed {total_processed} ended auction(s)'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ No ended auctions to process'))
