from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "sku", "category_name", "unit_price", "quantity", "line_total")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer", "status", "payment_status", "total", "is_demo", "created_at")
    list_filter = ("status", "payment_method", "payment_status", "is_demo")
    search_fields = ("order_number", "customer__username")
    inlines = [OrderItemInline]
    # Change order status via the NovaMart dashboard so stock stays consistent.
    readonly_fields = ("order_number", "status", "payment_status", "subtotal", "delivery_charge", "discount", "total")
