from django.shortcuts import render


def home(request):
    from articles.models import Article
    from items.services import get_merchant_context
    from pets.models import ElementType, Pet, Skill

    latest_articles = Article.objects.filter(
        is_published=True
    ).select_related('author').order_by('-created_at')[:3]

    context = {
        'latest_articles': latest_articles,
        'pet_count': Pet.objects.count(),
        'skill_count': Skill.objects.count(),
        'element_count': ElementType.objects.count(),
        'merchant': get_merchant_context(),
    }
    return render(request, 'core/home.html', context)
