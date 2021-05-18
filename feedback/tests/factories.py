import factory

from feedback import models


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Comment

    email = factory.Faker("email", domain="epa.gov")
    subject = factory.Faker("sentence")
    body = factory.Faker("paragraph")
