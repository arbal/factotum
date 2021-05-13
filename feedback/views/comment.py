from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import CreateView

from feedback.models.comment import Comment as CommentModel
from feedback.forms.comment_form import CommentForm


class CommentCreate(CreateView):
    model = CommentModel
    form_class = CommentForm
    template_name = "feedback/comment_create_modal.html"

    def form_invalid(self, form):
        return JsonResponse(form.errors, status=400)

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Comment received - thank you for your input.")
        return JsonResponse({"message": "success"})
