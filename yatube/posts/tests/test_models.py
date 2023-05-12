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

    def test_models_have_correct_object_names(self):
        """У моделей корректно работает __str__."""
        post = PostModelTest.post
        self.assertEqual(str(post), post.text[:MAX_SUMBOL])

    def test_model_group_have_correct_object_names(self):
        """У модели Group корректно работает __str__."""
        post_group = PostModelTest.group
        expected_object_name_group = post_group.title
        self.assertEqual(expected_object_name_group, str(post_group))
