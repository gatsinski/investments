from django import forms
from django.utils.translation import gettext_lazy as _


class ClosePositionForm(forms.Form):
    close_price = forms.DecimalField(label=_("Close price"))
