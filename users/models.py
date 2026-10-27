from django.db import models
from django.contrib.auth.models import User
from PIL import Image


# Extending User Model Using a One-To-One Link
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(default='default.jpg', upload_to='profile_images')
    bio = models.TextField()

    def __str__(self):
        return self.user.username

    # resizing images
    def save(self, *args, **kwargs):
        super().save()

        img = Image.open(self.avatar.path)

        if img.height > 100 or img.width > 100:
            new_img = (100, 100)
            img.thumbnail(new_img)
            img.save(self.avatar.path)


class UserPredictModel(models.Model):
    nitrogen = models.FloatField()
    phosphorus = models.FloatField()
    potassium = models.FloatField()
    temperature = models.FloatField()
    humidity = models.FloatField()
    ph = models.FloatField()
    rainfall = models.FloatField()
    label = models.CharField(max_length=100)  # This will store the prediction result

    def __str__(self):
        return f"Prediction: {self.label}"


class yield_db(models.Model):
    crop = models.CharField(max_length=100)
    season = models.CharField(max_length=100)
    area = models.FloatField()
    area_units = models.CharField(max_length=50)
    production = models.FloatField()
    production_units = models.CharField(max_length=50)
    yield_value = models.FloatField()  # This will store the prediction result

    def __str__(self):
        return f"{self.crop} - {self.season}"
