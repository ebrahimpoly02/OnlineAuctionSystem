from django.contrib import admin
from .models import User, Category, Auction, Bid, Payment, Rating, Watchlist, Report
admin.site.register(User)
admin.site.register(Category)
admin.site.register(Auction)
admin.site.register(Bid)
admin.site.register(Payment)
admin.site.register(Rating)
admin.site.register(Watchlist)
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['auction', 'reporter', 'reason', 'status', 'created_at']
    list_filter = ['status', 'reason', 'created_at']
    search_fields = ['auction__title', 'reporter__username', 'description']
    readonly_fields = ['created_at', 'reporter', 'auction']
    
    fieldsets = (
        ('Report Details', {
            'fields': ('auction', 'reporter', 'reason', 'description', 'created_at')
        }),
        ('Admin Review', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'admin_notes')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            if obj.status in ['reviewed', 'resolved', 'dismissed']:
                obj.reviewed_by = request.user
                from django.utils import timezone
                obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)
