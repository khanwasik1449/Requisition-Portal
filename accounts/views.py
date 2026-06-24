from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.contrib import messages
from .models import User


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

    def form_invalid(self, form):
        username = self.request.POST.get('username')
        if username:
            try:
                user = User.objects.get(username=username)
                if not user.is_active:
                    return render(self.request, 'accounts/login.html', {
                        'form': form,
                        'inactive_error': 'Your account is pending admin approval. Please try again later.',
                    })
            except User.DoesNotExist:
                pass
        return super().form_invalid(form)


def logout_view(request):
    logout(request)
    return redirect('login')


def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        role = request.POST.get('role', User.Role.REQUESTER)

        if password1 != password2:
            return render(request, 'accounts/signup.html', {'error': 'Passwords do not match'})

        if User.objects.filter(username=username).exists():
            return render(request, 'accounts/signup.html', {'error': 'Username already exists'})

        user = User.objects.create_user(
            username=username, password=password1,
            email=email, phone=phone, role=role,
            is_active=False
        )
        return render(request, 'accounts/pending_approval.html')

    return render(request, 'accounts/signup.html')


@login_required
@user_passes_test(lambda u: u.is_admin())
def user_list(request):
    users = User.objects.all().order_by('-is_active', 'date_joined')
    return render(request, 'accounts/user_list.html', {'users': users})


@login_required
@user_passes_test(lambda u: u.is_admin())
def user_approve(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.is_active = True
    user.save()
    messages.success(request, f'User "{user.username}" has been approved.')
    return redirect('user_list')


@login_required
@user_passes_test(lambda u: u.is_admin())
def user_deactivate(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'You cannot deactivate yourself.')
        return redirect('user_list')
    user.is_active = False
    user.save()
    messages.success(request, f'User "{user.username}" has been deactivated.')
    return redirect('user_list')


@login_required
@user_passes_test(lambda u: u.is_admin())
def user_create(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        role = request.POST['role']
        is_active = request.POST.get('is_active') == 'on'

        if User.objects.filter(username=username).exists():
            return render(request, 'accounts/user_form.html', {'error': 'Username already exists'})

        User.objects.create_user(
            username=username, password=password,
            email=email, phone=phone, role=role,
            is_active=is_active
        )
        messages.success(request, f'User "{username}" created.')
        return redirect('user_list')

    return render(request, 'accounts/user_form.html')


@login_required
@user_passes_test(lambda u: u.is_admin())
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user.email = request.POST.get('email', '')
        user.phone = request.POST.get('phone', '')
        user.role = request.POST['role']
        user.is_active = request.POST.get('is_active') == 'on'
        password = request.POST.get('password')
        if password:
            user.set_password(password)
        user.save()
        messages.success(request, f'User "{user.username}" updated.')
        return redirect('user_list')

    return render(request, 'accounts/user_form.html', {'edit_user': user})
