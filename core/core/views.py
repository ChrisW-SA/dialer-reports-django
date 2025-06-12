from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from core.decorators import redirect_authenticated_user

from django.db.models import Count, Avg, Sum, Max, Q, Case, When, IntegerField, Max, ExpressionWrapper, FloatField, F
from dialer_reports.models import CampaignRecord

def index(request):


    return redirect('login-page')


@redirect_authenticated_user
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            messages.error(request, 'Both email and password are required.')
            return render(request, 'core/login.html')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"{request.user} logged in!")
            return redirect('home-page')
        else:
            messages.error(request, 'Invalid email or password.')
            return render(request, 'core/login.html')
    return render(request, 'core/login.html')


@login_required
def logout_view(request):
    messages.success(request, f'{request.user} logged out!')
    logout(request)
    return redirect('login-page')


@login_required
def home(request):

    return render(request, "core/home.html", context={"sidebar_menu": "home-page"})


@login_required
def page_not_found(request):

    return redirect(request, '404.html')