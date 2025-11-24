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
    # Add multiple image field - NO widget parameter here!
    images = MultipleFileField(
        required=False,
        label='Upload Images (up to 5)'
    )
    
    class Meta:
        model = Auction
        fields = ['title', 'description', 'category', 'condition', 'starting_price', 
                  'minimum_bid_increment', 'buy_now_price', 'end_time', 
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
            'end_time': forms.DateTimeInput(attrs={
                'class': 'form-input',
                'type': 'datetime-local'
            }),
            'location': forms.Select(attrs={'class': 'form-select'}),
            'shipping_method': forms.RadioSelect(),
            'shipping_cost': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00 BHD (if applicable)',
                'step': '0.01'
            }),
        }