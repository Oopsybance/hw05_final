from django import forms
from django.test import Client, TestCase
from django.urls import reverse
from django.core.cache import cache

from ..models import Post, Group, User, Follow
from ..constants import TEST_FIRST_PAGE, TEST_SECOND_PAGE, TEST_MAX_POST


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        )
        cls.group_fake = Group.objects.create(
            title='Фейковая группа',
            slug='fake-slug',
            description='Описание фейк группы',
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def posts_check_all_fields(self, post):
        """Метод, проверяющий поля поста."""
        with self.subTest(post=post):
            self.assertEqual(post.id, self.post.id)
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.author, self.post.author)
            self.assertEqual(post.group.id, self.post.group.id)

    def test_views_use_correct_template(self):
        """URL-адреса использует соответствующий шаблон."""
        group = PostPagesTests.group
        user = PostPagesTests.user
        post = PostPagesTests.post
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    args=[group.slug]): 'posts/group_list.html',
            reverse(
                'posts:profile', args=[user.username]
            ): 'posts/profile.html',
            reverse('posts:post_detail',
                    args=[post.pk]): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    args=[post.pk]): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.posts_check_all_fields(response.context['page_obj'][0])

    def test_group_list_show_correct_context(self):
        """Шаблон group сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})))
        first_obj = response.context['page_obj'].object_list[0]
        self.posts_check_all_fields(first_obj)
        group_object = response.context['group']
        self.assertEqual(group_object.title, self.group.title)
        self.assertEqual(group_object.slug, self.group.slug)
        self.assertEqual(group_object.description, self.group.description)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})))
        first_obj = response.context['page_obj'].object_list[0]
        self.posts_check_all_fields(first_obj)
        author = response.context['author']
        self.assertEqual(author, self.user)

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
        group = response_group.context
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

    def test_auth_user_can_follow_author(self):
        """Проверка подписки на автора."""
        self.authorized_client.get(reverse(
            'posts:profile_follow', kwargs={'username': self.user2}))
        following = Follow.objects.filter(user=self.user, author=self.user2)
        self.assertTrue(following)
        self.authorized_client.get(reverse(
            'posts:profile_unfollow', kwargs={'username': self.user2}))
        unfollowing = Follow.objects.filter(user=self.user, author=self.user2)
        self.assertFalse(unfollowing)

    def test_posts_cache(self) -> None:
        """
        Проверки, которые проверяют работу кеша главной страницы(index).
        """
        response = self.client.get(reverse('posts:index'))
        content = response.content
        Post.objects.filter(group=self.group).delete()
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(content, response.content)
        cache.clear()
        response = self.client.get(reverse('posts:index'))
        self.assertNotEqual(content, response.content)

    def test_posts_detail_uses_correct_context_first_page(self) -> None:
        """Проверка изображения в context"""
        response = self.client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': 1}))
        self.assertIsNotNone(response.context['post'].image)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='NoName')
        cls.group = Group.objects.create(
            title="Тест",
            slug="slug",
            description="Тестовое описание"
        )
        cls.post = [Post.objects.create(
            author=cls.user,
            text=f"text{i}",
            group=cls.group
        ) for i in range(TEST_MAX_POST)]

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
                                 TEST_FIRST_PAGE)

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
