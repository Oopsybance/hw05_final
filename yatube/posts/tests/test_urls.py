from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User


class PostsUrlsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_name = User.objects.create_user(username='name')
        cls.user = User.objects.create_user(username='oopsy')
        cls.group = Group.objects.create(
            title='TestTitle',
            slug='test',
            description='TestDescription',
        )
        cls.post = Post.objects.create(
            text='TestText',
            author=cls.user,
        )
        cls.Post_detail = 'posts:post_detail'
        cls.Post_edit = 'posts:post_edit'

    def setUp(self):
        self.autorized_user = Client()
        self.autorized_user.force_login(self.user)
        self.not_author = Client()
        self.not_author.force_login(self.user_name)

    def test_urls_public_user(self):
        """Проверка на доступнотсь ссылок гостевому пользователю."""
        url_status = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.user.username}/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/': HTTPStatus.OK,
            '/unknow_page/': HTTPStatus.NOT_FOUND,
        }
        for url, status in url_status.items():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status)

    def test_autorized_url(self):
        """Проверка на доступнотсь ссылок авторезированному пользователю."""
        url_status = {
            '/create/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/edit/': HTTPStatus.OK,
            '/follow/': HTTPStatus.OK,
        }
        for url, status in url_status.items():
            with self.subTest(url=url):
                response = self.autorized_user.get(url)
                self.assertEqual(response.status_code, status)

    def test_create_edit_by_guest(self):
        """Проверка переадресации гостя при достпу на приватные страницы."""
        response = self.client.get(reverse(
            'posts:post_create'),
            follow=True)
        self.assertRedirects(
            response, reverse('users:login') + '?next=/create/')

    def test_edit_by_not_author(self):
        """Проверка переадресации при попытке редактировать чужой пост"""
        response = self.not_author.get(reverse(
            self.Post_edit, kwargs={'post_id': self.post.id}))
        self.assertRedirects(
            response, reverse(self.Post_detail,
                              kwargs={'post_id': self.post.id}))

    def test_accordance_urls_and_templates(self):
        """Проврка соответствия url и шаблонов"""
        url_templates_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/follow/': 'posts/follow.html',
        }
        for address, template in url_templates_names.items():
            with self.subTest(address=address):
                response = self.autorized_user.get(address)
                self.assertTemplateUsed(response, template)

    def test_cant_comment_post_guest(self):
        """Проверка переадресации гостя со страницы комментариев."""
        response = self.client.get(f'/posts/{self.post.pk}/comment/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(
            response, reverse('users:login') + '?next=/create/')

    def test_authorized_user_can_comment_post(self):
        """Проверка переадресации авторизированного пользователя
        на страницу поста."""
        response = self.client.get(
            f'/posts/{self.post.pk}/comment/'
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, f'/posts/{self.post.pk}/')
