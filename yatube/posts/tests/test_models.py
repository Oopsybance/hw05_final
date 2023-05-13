from django.test import TestCase

from ..models import Group, Post, User
from ..constants import MAX_SUMBOL


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Япония',
            slug='Japan',
            description='Инфорация'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Пост с написанным тестом',
            group=cls.group,
        )

    def test_models_and_group_str(self):
        """У моделей Models и Group работает __str__."""
        post = PostModelTest.post
        group = PostModelTest.group
        group_title = group.title
        fields_str = {
            self.post.text[:MAX_SUMBOL]: str(post),
            group_title: str(group),
        }
        for field, str_ in fields_str.items():
            with self.subTest(field=field):
                self.assertEqual(field, str_)
