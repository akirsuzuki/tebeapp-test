from django.contrib import admin
from .models import Category, Pref, Review


admin.site.register(Category)
admin.site.register(Pref)
admin.site.register(Review)