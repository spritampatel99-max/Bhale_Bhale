from django import forms

from accounts.forms import StyledFormMixin

from .models import Category, Product


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """Official Django pattern for multi-file uploads (docs: file-uploads)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "image/*"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(d, initial) for d in data if d]
        return [single_clean(data, initial)] if data else []


class CategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "slug", "description", "image", "is_active")
        help_texts = {"slug": "Leave blank to generate from the name."}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False
        self.fields["image"].widget.attrs.update({"accept": "image/*", "class": "input file"})

    def clean_slug(self):
        from django.utils.text import slugify

        slug = slugify(self.cleaned_data.get("slug", ""))
        if slug and Category.objects.filter(slug=slug).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This slug is already in use.")
        return slug


class ProductForm(StyledFormMixin, forms.ModelForm):
    extra_images = MultipleImageField(required=False, label="Additional photos")

    class Meta:
        model = Product
        fields = (
            "name", "category", "price", "original_price", "stock", "sku", "description",
            "image", "extra_images", "is_active", "is_featured", "rating", "rating_count",
        )
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}
        help_texts = {"sku": "Leave blank to auto-generate."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sku"].required = False
        self.fields["category"].queryset = Category.objects.order_by("name")
        for name in ("image", "extra_images"):
            self.fields[name].widget.attrs["class"] = "input file"
        self.fields["rating"].help_text = "Demo data only. Leave blank for no rating."
        self.fields["rating_count"].required = False

    def clean_rating_count(self):
        return self.cleaned_data.get("rating_count") or 0

    def clean_sku(self):
        sku = (self.cleaned_data.get("sku") or "").strip().upper()
        if sku and Product.objects.filter(sku=sku).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This SKU already exists.")
        return sku
