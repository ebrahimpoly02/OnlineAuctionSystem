from django import forms
from .models import Auction

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class AuctionForm(forms.ModelForm):
    # Add multiple image field
    images = MultipleFileField(
        required=False,
        label='Upload Images (up to 5)'
    )
    
    # Define location choices
    LOCATION_CHOICES = [
        ('', 'Select location'),
        ('Manama', 'Manama'),
        ('Muharraq', 'Muharraq'),
        ('Riffa', 'Riffa'),
        ('Hamad Town', 'Hamad Town'),
        ('Isa Town', 'Isa Town'),
        ('Sitra', 'Sitra'),
        ('Budaiya', 'Budaiya'),
        ('Jidhafs', 'Jidhafs'),
        ('A\'ali', 'A\'ali'),
        ('Tubli', 'Tubli'),
        ('Sanabis', 'Sanabis'),
        ('Adliya', 'Adliya'),
        ('Juffair', 'Juffair'),
        ('Seef', 'Seef'),
        ('Salmabad', 'Salmabad'),
    ]
    
    # Override location field with choices
    location = forms.ChoiceField(
        choices=LOCATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    
    # Add separate date and time fields for better UX
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        }),
        required=True,
        label='End Date'
    )
    
    end_time_hour = forms.IntegerField(
        min_value=0,
        max_value=12,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': '12',
            'min': '0',
            'max': '12'
        }),
        required=True,
        label='Hour'
    )
    
    end_time_minute = forms.IntegerField(
        min_value=0,
        max_value=59,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': '00',
            'min': '0',
            'max': '59'
        }),
        required=True,
        label='Minute'
    )
    
    end_time_period = forms.ChoiceField(
        choices=[('AM', 'AM'), ('PM', 'PM')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        label='AM/PM'
    )

    class Meta:
        model = Auction
        fields = ['title', 'description', 'category', 'condition', 'starting_price', 
                  'minimum_bid_increment', 'buy_now_price', 
                  'location', 'shipping_method', 'shipping_cost']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter auction title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Describe your item',
                'rows': 5
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'condition': forms.RadioSelect(),
            'starting_price': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00 BHD',
                'step': '0.01'
            }),
            'minimum_bid_increment': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '1.00 BHD',
                'step': '0.01'
            }),
            'buy_now_price': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Optional',
                'step': '0.01',
                'required': False
            }),
            'shipping_method': forms.RadioSelect(),
            'shipping_cost': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00 BHD (if applicable)',
                'step': '0.01'
            }),
        }