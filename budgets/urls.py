from rest_framework.routers import DefaultRouter
from budgets.views import BudgetViewSet

router = DefaultRouter()
router.register('budgets', BudgetViewSet, basename='budget')

urlpatterns = router.urls
