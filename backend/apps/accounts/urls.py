"""
URLs for accounts app.
"""
from django .urls import path ,include 
from rest_framework .routers import DefaultRouter 

from apps .accounts .views import (
LoginView ,LogoutView ,RefreshTokenView ,
BiometricEnrollView ,BiometricChallengeView ,BiometricLoginView ,
UserViewSet ,BiometricProfileViewSet ,
MFAStatusView ,MFASetupView ,MFAVerifyView ,MFADisableView ,MFALoginView ,
GlobalSearchView ,
PasswordResetRequestView ,PasswordResetConfirmView ,
GrantPermissionView ,RevokePermissionView ,
)

router =DefaultRouter ()
router .register (r'users',UserViewSet ,basename ='user')
router .register (r'biometric-profiles',BiometricProfileViewSet ,basename ='biometric-profile')

urlpatterns =[
path ('',include (router .urls )),
path ('login/',LoginView .as_view (),name ='login'),
path ('logout/',LogoutView .as_view (),name ='logout'),
path ('refresh/',RefreshTokenView .as_view (),name ='refresh'),
path ('biometric/enroll/',BiometricEnrollView .as_view (),name ='biometric-enroll'),
path ('biometric/challenge/',BiometricChallengeView .as_view (),name ='biometric-challenge'),
path ('biometric/login/',BiometricLoginView .as_view (),name ='biometric-login'),
# Comment_23
path ('2fa/status/',MFAStatusView .as_view (),name ='mfa-status'),
path ('2fa/setup/',MFASetupView .as_view (),name ='mfa-setup'),
path ('2fa/verify/',MFAVerifyView .as_view (),name ='mfa-verify'),
path ('2fa/disable/',MFADisableView .as_view (),name ='mfa-disable'),
path ('2fa/login/',MFALoginView .as_view (),name ='mfa-login'),
# Comment_24
path ('search/',GlobalSearchView .as_view (),name ='global-search'),
# Comment_25
path ('password/reset/',PasswordResetRequestView .as_view (),name ='password-reset'),
path ('password/reset/confirm/',PasswordResetConfirmView .as_view (),name ='password-reset-confirm'),
path ('users/<uuid:pk>/grant-permission/',GrantPermissionView .as_view (),name ='grant-permission'),
path ('users/<uuid:pk>/revoke-permission/',RevokePermissionView .as_view (),name ='revoke-permission'),
]
