from .models import Pref, Category

def common(request):
    """テンプレートに毎回渡すデータ"""
    context = {
        'pref_list': Pref.objects.all(),
        'category_list': Category.objects.all(),
    }

    return context

