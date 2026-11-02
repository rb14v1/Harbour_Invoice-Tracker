from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.clients.models import Client
from common.test_utils import auth_client, create_user


class ClientCrudTests(APITestCase):
    def setUp(self):
        self.user = create_user(email="clients@example.com")
        self.api = auth_client(self.user)

    def test_create_client(self):
        response = self.api.post(reverse("client-list"), {
            "name": "New Client", "email": "new@example.com", "phone": "555-1234",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(Client.objects.filter(user=self.user, name="New Client").exists())

    def test_blank_name_rejected(self):
        response = self.api.post(reverse("client-list"), {"name": "   ", "email": "x@example.com"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_only_returns_own_clients(self):
        Client.objects.create(user=self.user, name="Mine", email="mine@example.com")
        response = self.api.get(reverse("client-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [row["name"] for row in response.data["results"]]
        self.assertIn("Mine", names)
