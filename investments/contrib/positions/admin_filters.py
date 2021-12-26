from django.contrib import admin
from django.utils.translation import ugettext_lazy as _


class StatusFilter(admin.EmptyFieldListFilter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title = _("Status")

    def choices(self, changelist):
        for lookup, title in (
            (None, _("All")),
            ("1", _("Open")),
            ("0", _("Closed")),
        ):
            yield {
                "selected": self.lookup_val == lookup,
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg: lookup}
                ),
                "display": title,
            }
