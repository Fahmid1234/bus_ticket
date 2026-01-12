from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from .forms import CustomAuthenticationForm

# Add DRF imports
from rest_framework.routers import DefaultRouter
from .views_api import BusViewSet, RouteViewSet, ScheduleViewSet, UserViewSet, BookingViewSet, TicketViewSet, TemporarySeatSelectionViewSet

# Set up DRF router
router = DefaultRouter()
router.register(r'buses', BusViewSet)
router.register(r'routes', RouteViewSet)
router.register(r'schedules', ScheduleViewSet)
router.register(r'users', UserViewSet)
router.register(r'bookings', BookingViewSet)
router.register(r'tickets', TicketViewSet)
router.register(r'temporary-selections', TemporarySeatSelectionViewSet)

urlpatterns = [
    path('', views.home, name='home'),
    path('schedule/', views.schedule, name='schedule'),
    path('booking/', views.booking, name='booking'),
    path('contact/', views.contact, name='contact'),
    path('confirm-booking/', views.confirm_booking, name='confirm_booking'),
    
    # Payment URLs
    path('payment/<int:booking_id>/', views.payment, name='payment'),
    path('initiate-payment/', views.initiate_payment_view, name='initiate_payment'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-fail/', views.payment_fail, name='payment_fail'),
    path('payment-cancel/', views.payment_cancel, name='payment_cancel'),
    path('payment-ipn/', views.payment_ipn, name='payment_ipn'),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        authentication_form=CustomAuthenticationForm
    ), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('city-suggestions/', views.city_suggestions, name='city_suggestions'),
    path('download-invoice/', views.download_invoice, name='download_invoice'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('profile/', views.profile, name='profile'),
    path('check-email/', views.check_email, name='check_email'),
    path('resend-activation-email/', views.resend_activation_email, name='resend_activation_email'),
    path('password-change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change_form.html'), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'), name='password_change_done'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    # API URLs
    path('api/', include(router.urls)),
]
