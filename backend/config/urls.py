from django.urls import path, include, re_path
from django.http import HttpResponse
from django.conf import settings

def serve_spa(request):
    index_file = getattr(settings, 'FRONTEND_DIST', None)
    if index_file:
        index_html = index_file / "index.html"
        if index_html.exists():
            with open(index_html, "r", encoding="utf-8") as f:
                return HttpResponse(f.read(), content_type="text/html")
    return HttpResponse(
        "<h1>Weather-Aware Truck Routing Backend</h1>"
        "<p>API active at <code>/api/routes/</code> and <code>/api/heatmap/</code>.</p>"
        "<p>To serve the full frontend SPA, run <code>npm run build</code> in the frontend folder.</p>",
        content_type="text/html",
    )

urlpatterns = [
    path("api/", include("routing.urls")),
    re_path(r"^(?!api/).*$", serve_spa),
]
