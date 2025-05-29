from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name",)


class CustomUserAdmin(BaseUserAdmin):
    model = CustomUser
    list_display = ("email", "is_staff", "is_active", "organization", "user_image_tag")
    list_filter = ("is_staff", "is_superuser", "is_active", "organization")
    ordering = ("email",)
    search_fields = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "user_image", "organization")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "organization",
                    "user_image",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
    )

    def user_image_tag(self, obj):
        if obj.user_image:
            return format_html('<img src="{}" width="40" height="40" style="object-fit:cover;border-radius:50%;" />', obj.user_image.url)
        return "-"
    user_image_tag.short_description = "Image"


admin.site.register(CustomUser, CustomUserAdmin)
