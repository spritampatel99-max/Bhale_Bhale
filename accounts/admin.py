from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Address, User


@admin.register(User)
class NovaUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_staff", "is_active", "date_joined")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (("NovaMart", {"fields": ("role", "phone")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("NovaMart", {"fields": ("role", "phone", "email")}),)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "city", "state", "postal_code", "is_default")
    search_fields = ("user__username", "city", "postal_code")
