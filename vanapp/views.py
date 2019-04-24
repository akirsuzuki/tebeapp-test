from django.shortcuts import render, redirect
from django.views.generic import CreateView, ListView, UpdateView, DeleteView, TemplateView
import json
import time
import requests
from .models import Pref, Category, Review
from .forms import SearchForm, LoginForm, ReviewForm, SignUpForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView, LogoutView
)
from django.contrib import messages
from django.contrib.auth import login, authenticate

# スコアを出すため追加
from django.db.models import Avg

# ページネーションで追加
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


# グローバル関数として定義。どこからもkeyidを呼び出すことが出来る。
def get_keyid():
    return "296f76d7037341ade00e99ce1c5da7bb"


class IndexView(TemplateView):
    template_name = 'vanapp/index.html'

    def get_context_data(self, *args, **kwargs):
        searchform = SearchForm()
        #とりあえずトップページに出すものを取ってくる
        #get_gnavi_dataには辞書で渡す方法を考える
        query = get_gnavi_data("", "RSFST09000", "", "花見", 12)
        res_list = rest_search(query)
        total_hit_count = len(res_list)
        restaurants_info = extract_restaurant_info(res_list)
            
        # contextprocessorを設定後に消す
        # category_list = Category.objects.all().order_by('category_l')
        # pref_list = Pref.objects.all().order_by('pref')

        #review作成後に記述
        review_list = Review.objects.all()[:10]

        params = {
            'searchform': searchform,
            'restaurants_info': restaurants_info,
            # 'category_list': category_list,
            # 'pref_list': pref_list,
            'review_list': review_list
            }

        return params


# ページネーション用の関数
def paginate_queryset(request, queryset, count):
    paginator = Paginator(queryset, count)
    page = request.GET.get('page')
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    return page_obj


def Search(request):
    if request.method == 'GET':
        searchform = SearchForm(request.POST)

        if searchform.is_valid():
            category_l = request.GET['category_l']
            pref = request.GET['pref']
            freeword = request.GET['freeword']
            query = get_gnavi_data("", category_l, pref, freeword, 10)
            res_list = rest_search(query)
            total_hit_count = len(res_list)
            restaurants_info = extract_restaurant_info(res_list)

            # contextprocessorを設定後に消す
            # category_list = Category.objects.all().order_by('category_l')

    params = {
        'total_hit_count': total_hit_count,
        'title': 'リスト',
        'restaurants_info': restaurants_info,
        # 'category_list': category_list,
        }

    return render (request, 'vanapp/search.html', params)


def ShopInfo(request, restid):
    keyid = get_keyid()
    id = restid
    query = get_gnavi_data(id, "", "", "", 1)
    res_list = rest_search(query)
    restaurants_info = extract_restaurant_info(res_list)
    review_count = Review.objects.filter(shop_id=restid).count()
    score_ave = Review.objects.filter(shop_id = restid).aggregate(Avg('score'))
    average = score_ave['score__avg']
    if average:
        average_rate = average / 5 * 100
    else:
        average_rate = 0

    if request.method == 'GET':        
        review_form = ReviewForm()
        review_list = Review.objects.filter(shop_id = restid)

    else:
        form = ReviewForm(data=request.POST)
        score = request.POST['score']
        comment = request.POST['comment']

        if form.is_valid():
            review = Review()
            review.shop_id = restid
            review.shop_name = restaurants_info[0][1]
            review.shop_kana = restaurants_info[0][2]
            review.shop_address = restaurants_info[0][7]
            review.image_url = restaurants_info[0][5]
            review.user = request.user
            review.score = score
            review.comment = comment
            review.save()
            messages.success(request, 'レビューを投稿しました。')
            return redirect('vanapp:shop_info', restid)
        else:
            messages.error(request, 'エラーがあります。')
            return redirect('vanapp:shop_info', restid)
        return render(request, 'vanapp/index.html', {})

    params = {
        'title': '店舗詳細',
        'review_count': review_count,
        'restaurants_info': restaurants_info,
        'review_form': review_form,
        'review_list': review_list,
        'average': average,
        'average_rate': average_rate,
        }

    return render (request, 'vanapp/shop_info.html', params)


class Login(LoginView):
    form_class = LoginForm
    template_name = 'vanapp/login.html'


class Logout(LoginRequiredMixin, LogoutView):
    template_name = 'vanapp/logout.html'


class SignUp(CreateView):
    form_class = SignUpForm
    template_name = 'vanapp/signup.html'

    def post(self, request, *args, **kwargs):
        form = self.form_class(data=request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('vanapp:index')
        return render(request, 'vanapp/signup.html', {'form': form})



# 以下はビュー関数ではなく、機能の関数

# グルナビでの検索条件をクエリで取得する
def get_gnavi_data(id, category_l, pref, freeword, hit_per_page):
    keyid = get_keyid()
    # 一度に取得できる最大件数
    hit_per_page = hit_per_page
    # 店舗のid（グルナビ内で一意になっている）
    id = id
    # 大業態カテゴリ
    category_l = category_l
    #pref
    pref = pref
    #Freeword
    freeword = freeword
    #今回は関東地方のみ
    area = "AREA110"
    #パラメータ設定
    query = {"keyid": keyid, "id":id, "area":area, "pref":pref, "category_l":category_l,"hit_per_page":hit_per_page, "freeword":freeword}

    return query


# 実際にグルナビのサイトに掲載されいてるレストランを検索する関数
def rest_search(query):
    res_list = []
    res = json.loads(requests.get("https://api.gnavi.co.jp/RestSearchAPI/v3/", params=query).text)
    # レスポンスがerror でない場合に処理を開始する
    if "error" not in res:
        res_list.extend(res["rest"])
    return res_list


# rest_searchで取り出したデータを整理するための関数
def extract_restaurant_info(restaurants: 'restaurant response') -> 'restaurant list':
    restaurant_list = []
    for restaurant in restaurants:
        id = restaurant["id"]
        name = restaurant["name"]
        name_kana = restaurant["name_kana"]
        url = restaurant["url"]
        url_mobile = restaurant["url_mobile"]
        shop_image1 = restaurant["image_url"]["shop_image1"]
        shop_image2 = restaurant["image_url"]["shop_image2"]
        address = restaurant["address"]
        tel = restaurant["tel"]
        station_line = restaurant["access"]["line"]
        station = restaurant["access"]["station"]
        latitude = restaurant["latitude"]
        longitude = restaurant["longitude"]
        pr_long = restaurant["pr"]["pr_long"]

        # レビュー機能実装後に追加
        review_count = Review.objects.filter(shop_id = id).count()
        score_ave = Review.objects.filter(shop_id = id).aggregate(Avg('score'))
        average = score_ave['score__avg']
        if average:
            average_rate = average / 5 * 100
        else:
            average_rate = 0

        restaurant_list.append([id, name, name_kana, url, url_mobile, shop_image1, shop_image2, address, tel, station_line, station, latitude, longitude, pr_long, review_count, score_ave, average, average_rate])
    return restaurant_list


        
