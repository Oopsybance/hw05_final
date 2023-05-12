from django.core.paginator import Paginator

from .constants import POST_ON_PEGE


def get_page_paginator(request, posts):
    pagi = Paginator(posts, POST_ON_PEGE)
    page_number = request.GET.get('page')
    page_obj = pagi.get_page(page_number)
    return page_obj
