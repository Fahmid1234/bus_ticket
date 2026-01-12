from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from .models import User

class CustomUserCreationForm(UserCreationForm):
    """A custom form for creating new users, with email and phone fields."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'your.email@example.com'})
    )
    phone = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '01xxxxxxxxx'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'phone')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_classes = 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm pl-10'
        
        placeholders = {
            'username': 'Create a username',
            'email': 'your.email@example.com',
            'phone': '01xxxxxxxxx',
            'password': 'Create a password',
            'password2': 'Confirm your password',
        }

        for name, field in self.fields.items():
            # Add base classes and dynamic placeholder
            attrs = {'class': base_classes}
            if name in placeholders:
                attrs['placeholder'] = placeholders[name]
            field.widget.attrs.update(attrs)

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone.isdigit() or len(phone) != 11:
            raise forms.ValidationError('Please enter a valid 11-digit phone number.')
        return phone

class CustomAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                'Your account is inactive. Please check your email and activate your account before logging in.',
                code='inactive',
            )
    """A custom authentication form with styled widgets."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_classes = 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm pl-10'
        
        self.fields['username'].widget.attrs.update(
            {'class': base_classes, 'placeholder': 'Enter your username'}
        )
        self.fields['password'].widget.attrs.update(
            {'class': base_classes, 'placeholder': 'Enter your password'}
        )
        # The error-adding logic was here and has been removed.
        # Errors should be handled in the template. 

class ResendActivationEmailForm(forms.Form):
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'placeholder': 'your.email@example.com', 'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'})) 

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'phone']
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}))
    phone = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}))
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone.isdigit() or len(phone) != 11:
            raise forms.ValidationError('Please enter a valid 11-digit phone number.')
        return phone 