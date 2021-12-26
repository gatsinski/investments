from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from investments.contrib.positions.models import Position
from investments.contrib.securities.models import Bond
from investments.contrib.tags.models import Tag

from .models import DividendPayment, InterestPayment


def get_custom_titled_filter(title, filter_class):
    class Wrapper(filter_class):
        def __new__(cls, *args, **kwargs):
            instance = filter_class.create(*args, **kwargs)
            instance.title = title
            return instance

    return Wrapper


class BasePaymentsAdmin(admin.ModelAdmin):
    ordering = ("-recorded_on",)
    list_per_page = 100
    date_hierarchy = "recorded_on"
    list_display = (
        "amount",
        "position_link",
        "security_link",
        "position_units",
        "recorded_on",
        "tag_links",
        "user_link",
        "broker_link",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "position__security__user",
        "recorded_on",
        "created_at",
        "updated_at",
        "tags",
        (
            "position__broker__name",
            get_custom_titled_filter(_("Brokers"), admin.FieldListFilter),
        ),
        (
            "position__security__name",
            get_custom_titled_filter(_("Securities"), admin.FieldListFilter),
        ),
    )
    search_fields = ("position__security", "position__broker", "notes")
    autocomplete_fields = ("position",)

    @admin.display(
        ordering="position",
        description=_("Position"),
    )
    def position_link(self, payment):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse("admin:positions_position_change", args=(payment.position.pk,)),
                payment.position,
            )
        )

    @admin.display(
        ordering="position__units",
        description=_("Units"),
    )
    def position_units(self, payment):
        return payment.position.units.normalize()

    @admin.display(
        ordering="position__security",
        description=_("Security"),
    )
    def security_link(self, payment):
        security = payment.position.security

        try:
            if security.bond:
                reverse_string = "admin:securities_bond_change"
        except Bond.DoesNotExist:
            reverse_string = "admin:securities_stock_change"

        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse(reverse_string, args=(security.pk,)), security
            )
        )

    @admin.display(
        description=_("Tags"),
    )
    def tag_links(self, payment):
        tag_links = [
            '<a href="{}">{}</a>'.format(
                reverse("admin:tags_tag_change", args=(tag.pk,)),
                tag,
            )
            for tag in payment.tags.all()
        ]

        return mark_safe(" ".join(tag_links))

    @admin.display(
        ordering="user",
        description=_("User"),
    )
    def user_link(self, payment):
        user = payment.position.security.user

        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse("admin:users_user_change", args=(user.pk,)),
                user.email,
            )
        )

    @admin.display(
        ordering="position__broker",
        description=_("Broker"),
    )
    def broker_link(self, payment):
        broker = payment.position.broker

        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse("admin:brokers_broker_change", args=(broker.pk,)),
                broker,
            )
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "position",
                "position__broker",
                "position__security",
                "position__security__user",
                "position__security__bond",
                "position__security__stock",
            )
            .prefetch_related(
                "tags",
            )
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        form.base_fields["position"].queryset = Position.objects.filter(
            security__user=request.user
        )
        form.base_fields["tags"].queryset = Tag.objects.filter(author=request.user)

        return form


@admin.register(DividendPayment)
class DividendPaymentsAdmin(BasePaymentsAdmin):
    def get_list_display(self, request):
        list_display = list(self.list_display)

        list_display.insert(1, "type")

        return list_display

    def get_list_filter(self, request):
        list_filter = list(self.list_filter)

        list_filter.insert(1, "type")

        return list_filter


@admin.register(InterestPayment)
class InterestPaymentsAdmin(BasePaymentsAdmin):
    pass
