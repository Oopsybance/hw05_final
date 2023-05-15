from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from ..models import Post, Group, User, Comment


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='admin')
        cls.group = Group.objects.create(
            title='Япония',
            slug='Japan',
            description='Инфорация'
        )
        cls.group2 = Group.objects.create(
            title='Вторая группа',
            slug='group2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Пост с текстом',
            group=cls.group,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Проверка, создает ли форма пост в базе."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        posts = list(Post.objects.values_list('id', flat=True))
        form_data = {
            'text': 'Пост с написанным тестом',
            'group': PostFormTests.group.pk,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        posts_update = Post.objects.exclude(id__in=posts)
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': PostFormTests.user.username}
        ))
        expected_count = len(posts) + 1
        self.assertEqual(Post.objects.count(), expected_count)
        post_new = posts_update[0]
        self.assertEqual(post_new.text, form_data['text'])
        self.assertEqual(post_new.author, PostFormTests.user)
        self.assertEqual(post_new.group, PostFormTests.group)
        self.assertEqual(post_new.image, 'posts/' + uploaded.name)

    def test_edit_post(self):
        """Проверка, редактируется ли пост."""
        form_data = {
            'text': 'Измененный старый пост',
            'group': PostFormTests.group2.pk,
        }
        self.authorized_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostFormTests.post.pk}
            ),
            data=form_data,
            follow=True
        )
        post = Post.objects.get(pk=PostFormTests.post.pk)
        response = self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': PostFormTests.post.pk}
        ))
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group, self.group2)
        self.assertEqual(post.author, self.user)

    def test_comment_for_authorized_user(self):
        """Тест создания комментария авторизованным пользователем"""
        comments = list(Comment.objects.values_list('id', flat=True))
        form_data = {
            'text': 'новый комментарий'
        }
        comments_updade = Comment.objects.exclude(id__in=comments)
        expected_count = len(comments) + 1
        new_comment = comments_updade[0]
        self.assertEqual(self.post.comments.count(), expected_count)
        self.assertEqual(new_comment.text, form_data['text'])
        self.assertEqual(new_comment.author, self.user)
        self.assertEqual(form_data['text'], new_comment.text)

    def test_new_comment_guests_client(self):
        """Гость не может добавлять комментарий."""
        comments = Comment.objects.count()
        form_data = {
            'text': 'Новый комментарий',
        }
        self.client.post(
            reverse('posts:add_comment', kwargs={
                'post_id': self.post.id
            }),
            data=form_data,
            follow=True
        )
        response = self.client.post(
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id}))
        self.assertEqual(Comment.objects.count(), comments)
        self.assertFalse(response.context['comments'])
