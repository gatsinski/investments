from django.contrib import admin
from django.contrib.admin import helpers
from django.core.checks import messages
from django.db.models import F
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django_object_actions import DjangoObjectActions

from investments.contrib.brokers.models import Broker
from investments.contrib.securities.models import Bond, Security
from investments.contrib.tags.models import Tag

from .forms import ClosePositionForm
from .models import Position
from .admin_filters import StatusFilter


def custom_titled_filter(title, filter_class):
    class Wrapper(filter_class):
        def __new__(cls, *args, **kwargs):
            instance = filter_class.create(*args, **kwargs)
            instance.title = title
            return instance

    return Wrapper


@admin.register(Position)
class PositionsAdmin(DjangoObjectActions, admin.ModelAdmin):
    list_filter = (
        "security__user",
        "opened_at",
        "closed_at",
        ("closed_at", StatusFilter),
        "created_at",
        "updated_at",
        "tags",
        "security__stock__sector",
        ("broker__name", custom_titled_filter(_("Brokers"), admin.FieldListFilter)),
        (
            "security__name",
            custom_titled_filter(_("Securities"), admin.FieldListFilter),
        ),
    )
    list_display = (
        "position_id",
        "security_link",
        "sector",
        "normalized_units",
        "opened_at",
        "normalized_open_price",
        "open_amount",
        "closed_at",
        "normalized_close_price",
        "close_amount",
        "profit_or_loss",
        "tag_links",
        "user_link",
        "broker_link",
        "created_at",
        "updated_at",
    )

    list_per_page = 100
    ordering = ("-opened_at",)
    date_hierarchy = "opened_at"
    search_fields = ("position_id", "notes", "security__name", "security__stock__symbol")
    autocomplete_fields = ("security",)
    change_actions = ("close_position", "open_position")

    @admin.display(
        ordering="security",
        description=_("Security"),
    )
    def security_link(self, position):
        try:
            if position.security.bond:
                reverse_string = "admin:securities_bond_change"
        except Bond.DoesNotExist:
            reverse_string = "admin:securities_stock_change"

        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse(reverse_string, args=(position.security.pk,)), position.security
            )
        )

    @admin.display(
        ordering="security__stock__sector",
        description=_("Sector"),
    )
    def sector(self, position):
        return position.security.stock.get_sector_display()

    @admin.display(
        ordering="units",
        description=_("Units"),
    )
    def normalized_units(self, position):
        return position.units.normalize()

    @admin.display(
        ordering="open_price",
        description=_("Open price"),
    )
    def normalized_open_price(self, position):
        return position.open_price.normalize()

    @admin.display(
        ordering="close_price",
        description=_("Close price"),
    )
    def normalized_close_price(self, position):
        return position.close_price.normalize() if position.close_price else None

    @admin.display(
        ordering=F("open_price") * F("units"),
        description=_("Open amount"),
    )
    def open_amount(self, position):
        return position.open_amount

    @admin.display(
        ordering=F("close_price") * F("units"),
        description=_("Close amount"),
    )
    def close_amount(self, position):
        return position.close_amount

    @admin.display(
        ordering=F("close_price") * F("units") - F("open_price") * F("units"),
        description=_("P/L"),
    )
    def profit_or_loss(self, position):
        return position.profit_or_loss

    @admin.display(
        description=_("Tags"),
    )
    def tag_links(self, position):
        tag_links = [
            '<a href="{}">{}</a>'.format(
                reverse("admin:tags_tag_change", args=(tag.pk,)),
                tag,
            )
            for tag in position.tags.all()
        ]

        return mark_safe(" ".join(tag_links))

    @admin.display(
        ordering="security__user",
        description=_("User"),
    )
    def user_link(self, position):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse("admin:users_user_change", args=(position.security.user.pk,)),
                position.security.user.email,
            )
        )

    @admin.display(
        ordering="broker",
        description=_("Broker"),
    )
    def broker_link(self, position):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse("admin:brokers_broker_change", args=(position.broker.pk,)),
                position.broker,
            )
        )

    def get_change_actions(self, request, position_id, form_url):
        actions = list(super().get_change_actions(request, position_id, form_url))
        position = self.model.objects.get(pk=position_id)

        if position.is_closed:
            actions.remove("close_position")
        else:
            actions.remove("open_position")

        return actions

    def close_position(self, request, position, *args, **kwargs):
        if position.is_closed:
            self.message_user(request, _("The position is already closed"))

            return redirect(
                "admin:positions_position_change", object_id=str(position.pk)
            )

        if "apply" in request.POST:
            form = ClosePositionForm(request.POST)

            if form.is_valid():
                cleaned_data = form.cleaned_data
                position.close_price = cleaned_data.get("close_price")
                position.closed_at = timezone.now()
                position.save()

                self.message_user(request, _("The position was successfully closed"))

                return redirect(
                    "admin:positions_position_change", object_id=str(position.pk)
                )
        else:
            form = ClosePositionForm()

        adminForm = helpers.AdminForm(
            form=form,
            fieldsets=((None, {"fields": ("close_price",)}),),
            prepopulated_fields={},
            readonly_fields=[],
            model_admin=self,
        )

        return render(
            request,
            "admin/positions/close_position_form.html",
            context={
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "adminForm": adminForm,
                "object": position,
            },
        )

    def open_position(self, request, position):
        if position.is_closed:
            position.closed_at = None
            position.close_price = None
            position.save()
            self.message_user(request, _("The position was successfully opened"))
        else:
            self.message_user(
                request, _("The position is already open"), level=messages.WARNING
            )

        return redirect("admin:positions_position_change", object_id=str(position.pk))

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "security",
                "broker",
                "security__user",
                "security__bond",
                "security__stock",
            )
            .prefetch_related(
                "tags",
            )
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        form.base_fields["security"].queryset = Security.objects.filter(
            user=request.user
        )
        form.base_fields["broker"].queryset = Broker.objects.filter(user=request.user)
        form.base_fields["tags"].queryset = Tag.objects.filter(author=request.user)

        form.base_fields["broker"].initial = form.base_fields["broker"].queryset.first()

        return form

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )

        if "autocomplete/" in request.path:
            queryset = queryset.filter(security__user=request.user)

        return queryset, use_distinct
