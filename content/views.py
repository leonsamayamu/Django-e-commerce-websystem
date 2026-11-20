from django.shortcuts import render

from .models import AboutPage, AboutPhoto, AboutSection


def about(request):
    return render(request, "content/about.html", {
        "page": AboutPage.load(), "sections": AboutSection.objects.all(), "photos": list(AboutPhoto.objects.all())})
