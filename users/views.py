import base64
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import joblib
import matplotlib
matplotlib.use('Agg')  # render plots without a GUI window (needed inside a web server)
import matplotlib.pyplot as plt
import numpy as np
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from .forms import (LoginForm, RegisterForm, UpdateProfileForm,
                    UpdateUserForm, UserPredictDataForm)
from .models import UserPredictModel, yield_db

BASE_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=None)
def load_model(filename):
    """Load a trained model that lives next to this file (e.g. users/crop1.pkl).

    Models are loaded on first use, and a clear error is raised if the file is
    missing (crop1.pkl is created by notebooks/crop_recommendation_model.ipynb).
    """
    path = BASE_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"The trained model '{filename}' is not available yet.")
    return joblib.load(path)


# NOTE: home() and index() are referenced in users/urls.py but their code is not
# in the project report's appendix. These are minimal placeholders.
def home(request):
    return render(request, 'users/home.html')


def index(request):
    return render(request, 'users/index.html')


# NOTE: the imports and the class header of RegisterView were not visible in the
# report's appendix (it starts mid-class); they are reconstructed here.
class RegisterView(View):
    form_class = RegisterForm
    initial = {'key': 'value'}
    template_name = 'users/register.html'

    def dispatch(self, request, *args, **kwargs):
        # will redirect to the home page if a user tries to access the register page while logged in
        if request.user.is_authenticated:
            return redirect(to='/')

        # else process dispatch as it otherwise normally would
        return super(RegisterView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            form.save()

            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}')

            return redirect(to='login')

        return render(request, self.template_name, {'form': form})


# Class based view that extends from the built in login view to add a remember me functionality
class CustomLoginView(LoginView):
    form_class = LoginForm

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')

        if not remember_me:
            # set session expiry to 0 seconds. So it will automatically close the session after the browser is closed.
            self.request.session.set_expiry(0)

            # Set session as modified to force data updates/cookie to be saved.
            self.request.session.modified = True

        # else browser session will be as long as the session cookie time "SESSION_COOKIE_AGE" defined in settings.py
        return super(CustomLoginView, self).form_valid(form)


class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    subject_template_name = 'users/password_reset_subject'
    success_message = "We've emailed you instructions for setting your password, " \
                      "if an account exists with the email you entered. You should receive them shortly." \
                      " If you don't receive an email, " \
                      "please make sure you've entered the address you registered with, and check your spam folder."
    success_url = reverse_lazy('users-home')


class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'users/change_password.html'
    success_message = "Successfully Changed Your Password"
    success_url = reverse_lazy('users-home')


@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UpdateUserForm(request.POST, instance=request.user)
        profile_form = UpdateProfileForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile is updated successfully')
            return redirect(to='users-profile')
    else:
        user_form = UpdateUserForm(instance=request.user)
        profile_form = UpdateProfileForm(instance=request.user.profile)

    return render(request, 'users/profile.html', {'user_form': user_form, 'profile_form': profile_form})


def Deploy_8(request):
    """Crop prediction: soil and weather inputs -> recommended crop."""
    if request.method == 'POST':
        form = UserPredictDataForm(request.POST)
        if form.is_valid():
            # Extract cleaned data from form
            nitrogen = form.cleaned_data['nitrogen']
            phosphorus = form.cleaned_data['phosphorus']
            potassium = form.cleaned_data['potassium']
            temperature = form.cleaned_data['temperature']
            humidity = form.cleaned_data['humidity']
            ph = form.cleaned_data['ph']
            rainfall = form.cleaned_data['rainfall']

            # Prepare features for prediction
            features = np.array([[nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall]])

            # Predict using the loaded model
            try:
                model = load_model('crop1.pkl')
            except FileNotFoundError as exc:
                messages.error(request, str(exc))
                return render(request, 'app/deploy_8.html', {'form': form})
            prediction = model.predict(features)
            prediction = prediction[0]

            # Determine the result based on prediction
            crops = ['Apple', 'Banana', 'BlackGram', 'Chickpea', 'Coconut', 'Coffee', 'Cotton', 'Grapes', 'Jute',
                     'KidneyBeans', 'Lentil', 'Maize', 'Mango', 'MothBeans', 'MungBean', 'Musk melon', 'Orange',
                     'Papaya', 'Pigeonpeas', 'Pomegranate', 'Rice', 'Watermelon']
            result = crops[prediction]

            # Save data to database
            instance = form.save(commit=False)
            instance.label = result
            instance.save()

            # Render output page with prediction result
            return render(request, 'app/output1.html', {'prediction_text': result})
    else:
        form = UserPredictDataForm()

    return render(request, 'app/deploy_8.html', {'form': form})


def Deploy_9(request):
    """Yield prediction: crop, season, area, production -> predicted yield."""
    if request.method == "POST":
        # Extract features from the POST request
        int_features = [x for x in request.POST.values()]
        int_features = int_features[1:]  # the first value is the CSRF token

        # Convert features to numpy array
        final_features = [np.array(int_features, dtype=object)]

        # Make prediction using the model
        try:
            model = load_model('YIELD.pkl')
        except FileNotFoundError as exc:
            messages.error(request, str(exc))
            return render(request, 'app/Deploy_9.html')
        prediction = model.predict(final_features)
        output = prediction[0]

        # Save the data to the database
        yield_instance = yield_db(
            crop=request.POST['crop'],
            season=request.POST['season'],
            area=request.POST['area'],
            area_units=request.POST['area_units'],
            production=request.POST['production'],
            production_units=request.POST['production_units'],
            yield_value=output
        )
        yield_instance.save()

        # Generate plot
        categories = ['crop', 'season', 'area', 'area_units', 'production', 'production_units', 'yield_value']
        values = [request.POST['crop'], request.POST['season'], request.POST['area'],
                  request.POST['area_units'], request.POST['production'],
                  request.POST['production_units'], output]

        # Convert categorical data to strings for plotting
        str_values = [str(value) for value in values]

        plt.figure(figsize=(10, 6))
        plt.plot(categories, str_values, marker='o', color='red')
        plt.xlabel('Categories')
        plt.ylabel('Values')
        plt.title('Crop Yield Prediction')

        # Save the plot to a buffer
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        buffer.seek(0)

        # Encode plot to base64 string
        plot_base64 = base64.b64encode(buffer.read()).decode('utf-8')

        # Create context for rendering the template
        context = {
            'plot_base64': plot_base64,
            'prediction_text1': f'The yield is {output}, indicating the amount of agricultural product harvested.'
        }

        return render(request, 'app/output.html', context)
    else:
        return render(request, 'app/Deploy_9.html')


def Basic_report(request):
    return render(request, 'app/Basic_report.html')


def Metrics_report(request):
    return render(request, 'app/Metrics_report.html')


def Yield_report(request):
    return render(request, 'app/Yield_report.html')


def Crop(request):
    data = UserPredictModel.objects.all()
    return render(request, 'app/crop_db.html', {'data': data})


def Yield(request):
    data = yield_db.objects.all()
    return render(request, 'app/yield_db.html', {'data': data})


def logout_view(request):
    auth_logout(request)
    return redirect('/')
