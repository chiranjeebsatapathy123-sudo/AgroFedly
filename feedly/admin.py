from django.contrib import admin
from .models import (
    MealRecord, DemandForecast, Organization, OrganizationMember,
    Recipient, SurplusFood, Redistribution, Delivery, Ingredient,
    AgriculturalProduce, ProcessingRecord, AgriculturalSupplyRequest,
    BuyerDemand, SupplyMatch
)

admin.site.register(MealRecord)
admin.site.register(DemandForecast)
admin.site.register(Organization)
admin.site.register(OrganizationMember)
admin.site.register(Recipient)
admin.site.register(SurplusFood)
admin.site.register(Redistribution)
admin.site.register(Delivery)
admin.site.register(Ingredient)
admin.site.register(AgriculturalProduce)
admin.site.register(ProcessingRecord)
admin.site.register(AgriculturalSupplyRequest)
admin.site.register(BuyerDemand)
admin.site.register(SupplyMatch)
