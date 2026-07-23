from django.shortcuts import get_object_or_404, render
from .models import Article


def article_list(request):
    category = request.GET.get('category', '')
    articles = Article.objects.filter(is_published=True)

    if category:
        articles = articles.filter(category=category)

    articles = articles.order_by('-created_at')

    categories = Article.CATEGORY_CHOICES

    context = {
        'articles': articles,
        'categories': categories,
        'current_category': category,
    }
    return render(request, 'articles/article_list.html', context)


def article_detail(request, article_id):
    article = get_object_or_404(Article, pk=article_id, is_published=True)
    return render(request, 'articles/article_detail.html', {'article': article})
