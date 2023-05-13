from django.views.generic.base import TemplateView


class AboutAuthorView(TemplateView):
    """Вывод информации об авторе проекта."""
    template_name = 'about/author.html'


class AboutTechView(TemplateView):
    """Вывод информации об использованных технологиях."""
    template_name = 'about/tech.html'
