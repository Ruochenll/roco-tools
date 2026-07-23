from django.shortcuts import render


def home(request):
    from articles.models import Article

    latest_articles = Article.objects.filter(
        is_published=True
    ).select_related('author').order_by('-created_at')[:8]

    context = {
        'latest_articles': latest_articles,
    }
    return render(request, 'core/home.html', context)
