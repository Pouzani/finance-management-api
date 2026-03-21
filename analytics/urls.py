from django.urls import path
from analytics.views import MonthlyFlowView, CategorySplitView

urlpatterns = [
    path('analytics/monthly-flow/', MonthlyFlowView.as_view(), name='monthly-flow'),
    path('analytics/category-split/', CategorySplitView.as_view(), name='category-split'),
]
