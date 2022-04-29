from django.utils.translation import gettext_lazy as _

# GISC is documented here - https://www.msci.com/documents/1296102/11185224/GICS+Methodology+2020.pdf
ENERGY = 10
MATERIALS = 15
INDUSTRIALS = 20
CONSUMER_DISCRETIONARY = 25
CONSUMER_STAPLES = 30
HEALTH_CARE = 35
FINANCIALS = 40
INFORMATION_TECHNOLOGY = 45
COMMUNICATION_SERVICES = 50
UTILITIES = 55
REAL_ESTATE = 60

SECTOR_CHOICES = (
    (ENERGY, _("Energy")),
    (MATERIALS, _("Materials")),
    (INDUSTRIALS, _("Industrials")),
    (CONSUMER_DISCRETIONARY, _("Consumer Discretionary")),
    (CONSUMER_STAPLES, _("Consumer Staples")),
    (HEALTH_CARE, _("Health Care")),
    (FINANCIALS, _("Financials")),
    (INFORMATION_TECHNOLOGY, _("Information Technology")),
    (COMMUNICATION_SERVICES, _("Communication Services")),
    (UTILITIES, _("Utilities")),
    (REAL_ESTATE, _("Real Estate")),
)

COMMON_STOCK = "common_stock"
PREFERRED_STOCK = "preferred_stock"

STOCK_TYPE_CHOICES = (
    (COMMON_STOCK, _("Common stock")),
    (PREFERRED_STOCK, _("Preferred stock")),
)

GOVERNMENT_BOND = "government_bond"
CORPORATE_BOND = "corporate_bond"

BOND_TYPE_CHOICES = (
    (GOVERNMENT_BOND, _("Government bond")),
    (CORPORATE_BOND, _("Corporate bond")),
)
