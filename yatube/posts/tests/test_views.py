from django import forms
from django.test import Client, TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.core.cache import cache
from django.core.paginator import Page

from ..models import Post, Group, User, Follow
from ..constants import POST_ON_PEGE, TEST_SECOND_PAGE


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        image = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=image,
            content_type='image/gif',
        )
        cls.user = User.objects.create(username='NoName')
        cls.group = Group.objects.create(
            title='Тестовый заголовок группы',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def post_get_on_first_page(self, page_obj):
        return page_obj[0]

    def posts_check_all_fields(self, post):
        """Метод, проверяющий поля поста."""
        with self.subTest(post=post):
            self.assertEqual(post.id, self.post.id)
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.author, self.post.author)
            self.assertEqual(post.group.id, self.post.group.id)
            self.assertEqual(post.image, self.post.image)

    def test_views_use_correct_template(self):
        """URL-адреса использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    args=[self.group.slug]): 'posts/group_list.html',
            reverse(
                'posts:profile', args=[self.user.username]
            ): 'posts/profile.html',
            reverse('posts:post_detail',
                    args=[self.post.pk]): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    args=[self.post.pk]): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        page_obj = response.context.get('page_obj')
        post = self.post_get_on_first_page(page_obj)
        self.assertIsInstance(page_obj, Page)
        self.posts_check_all_fields(post)

    def test_group_list_show_correct_context(self):
        """Шаблон group сформирован с правильным контекстом."""
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        page_obj = response.context.get('page_obj')
        post = self.post_get_on_first_page(page_obj)
        self.assertIsInstance(page_obj, Page)
        self.assertEqual(response.context.get('group'), self.group)
        self.posts_check_all_fields(post)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.user})
        )
        page_obj = response.context.get('page_obj', None)
        post = self.post_get_on_first_page(page_obj)
        self.assertIsInstance(page_obj, Page)
        self.assertEqual(response.context.get('author'), self.user)
        self.posts_check_all_fields(post)
        following = response.context.get('following')
        self.assertFalse(following)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}),
        )
        first_object = response.context['post']
        self.posts_check_all_fields(first_object)

    def test_post_create_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'group': forms.fields.ChoiceField,
            'text': forms.fields.CharField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_edit_context(self):
        """Шаблон post_edit  с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_new_post_not_in_another_group(self):
        """Проверка сохранение поста"""
        post = Post.objects.create(
            text='Новый тестовой пост',
            author=self.user,
            group=self.group,
        )
        response_group = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.post.id})
        )
        group = response_group.context[0]
        self.assertNotIn(post, group)

    def test_check_in_pages(self):
        """Проверка поста на страницах главной, группе, профиле"""
        post_new = Post.objects.create(
            text='Новый пост с текстом',
            author=self.user,
            group=self.group,
        )
        urls = [
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': self.user}),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
        ]
        for url in urls:
            response = self.authorized_client.get(url)
            with self.subTest(url=url):
                page_obj = response.context.get('page_obj')
                self.assertEqual(page_obj[0], post_new)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='NoName')
        cls.group = Group.objects.create(
            title='Тест',
            slug='slug',
            description='Тестовое описание'
        )
        cls.post = [Post.objects.create(
            author=cls.user,
            text=f'text{i}',
            group=cls.group
        ) for i in range(POST_ON_PEGE + TEST_SECOND_PAGE)]

    def test_first_page(self):
        templates_pages_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html':
                reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            'posts/profile.html':
                reverse('posts:profile', kwargs={'username': self.user}),
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']),
                                 POST_ON_PEGE)

    def test_second_page(self):
        """Проверка количества постов на второй странице."""
        templates_pages_names = {
            'posts/index.html': reverse('posts:index') + '?page=2',
            'posts/group_list.html':
                reverse('posts:group_list',
                        kwargs={'slug': self.group.slug}) + '?page=2',
            'posts/profile.html':
                reverse('posts:profile',
                        kwargs={'username': self.user}) + '?page=2',
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']),
                                 TEST_SECOND_PAGE)


class FollowTests(TestCase):
    """Тесты на проверку подписок."""
    class FollowViewsTest(TestCase):
        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            cls.user = User.objects.create_user('test_author')
            cls.user_follow = User.objects.create_user('user_follow')
            cls.user_unfollow = User.objects.create_user('user_unfollow')
            cls.post_1 = Post.objects.create(
                text='Подпишись на меня',
                author=cls.user_follow
            )
            cls.post_2 = Post.objects.create(
                text='Подпишись на меня',
                author=cls.user_unfollow
            )

        def setUp(self):
            cache.clear()
            self.authorized_client_follow = Client()
            self.authorized_client_follow.force_login(self.user_follow)
            self.authorized_client_unfollow = Client()
            self.authorized_client_unfollow.force_login(self.user_unfollow)

        def test_post_profile_follow(self):
            """Проверка подписки на пользователя."""
            follow = Follow.objects.filter(
                user=self.user, author=self.user_follow
            ).exists()
            self.authorized_client_follow.get(
                reverse(
                    'posts:profile_follow',
                    kwargs={'username': self.user_follow.username}
                )
            )
            follow_upd = Follow.objects.filter(
                user=self.user, author=self.user_follow
            ).exists()
            self.assertFalse(follow)
            self.assertTrue(follow_upd)

        def test_post_profile_unfollow(self):
            """Проверка отписки от пользователя."""
            unfollow = Follow.objects.filter(
                user=self.user, author=self.user_unfollow
            ).exists()
            self.authorized_client_unfollow.get(
                reverse(
                    'posts:profile_unfollow',
                    kwargs={'username': self.user_unfollow.username}
                )
            )
            unfollow_upd = Follow.objects.filter(
                user=self.user, author=self.user_unfollow
            ).exists()
            self.assertTrue(unfollow)
            self.assertFalse(unfollow_upd)

        def test_follower_sees_following_author_posts(self):
            """Проверка наличия постов у подписчика."""
            response = self.authorized_client_follow.get(
                reverse('posts:follow_index'))
            self.assertIn(self.post_1, response.context.get('page_obj'))

        def test_follower_not_sees_stranger_posts(self):
            """Проверка, не попадат ли пост, если не подписчик."""
            response = self.authorized_client_unfollow.get(
                reverse('posts:follow_index'))
            self.assertNotIn(self.post_2, response.context.get('page_obj'))


class CacheViewsTest(TestCase):
    """Тесты на проверку кеширования."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user('post_author')
        cls.group = Group.objects.create(
            title='Название группы',
            slug='slug',
            description='Описание группы',
        )
        cls.post = Post.objects.create(
            text='Текст',
            author=cls.user,
            group=cls.group,
        )

    def test_cache_index(self):
        """Проверка хранения и очищения кэша для index."""
        response = self.client.get(reverse('posts:index'))
        Post.objects.create(
            text='New post',
            author=self.user,
        )
        response_old = self.client.get(reverse('posts:index'))
        self.assertEqual(
            response.content,
            response_old.content
        )
        cache.clear()
        response_new = self.client.get(reverse('posts:index'))
        self.assertNotEqual(
            response.content,
            response_new.content
        )
