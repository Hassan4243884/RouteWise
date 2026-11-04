from django.urls import path
from .views import RouteView, HeatmapView

urlpatterns = [
    path("routes/", RouteView.as_view(), name="routes"),
    path("heatmap/", HeatmapView.as_view(), name="heatmap"),
]
