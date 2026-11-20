from django.db import models

from content.models import Singleton


class AssistantSettings(Singleton):
    enabled = models.BooleanField(default=True)
    name = models.CharField(max_length=40, default="Shop assistant")
    greeting = models.CharField(max_length=300, default="Hi! I can answer questions about this shop. What would you like to know?")
    extra_instructions = models.TextField(blank=True, max_length=1500,
                                          help_text="Extra tone or style guidance, e.g. 'Be brief and friendly.' It can never override the built-in safety rules.")
    fallback_message = models.CharField(max_length=300, default="Sorry, I can't help with that here. Please use the Contact page and our team will get back to you.")
    use_ai = models.BooleanField("Use AI for free-text questions", default=True,
                                 help_text="When off (or when no API key is configured) only the commands below are answered.")
    max_messages_per_day = models.PositiveSmallIntegerField(default=30, help_text="Per visitor, to control cost and abuse.")

    class Meta:
        verbose_name_plural = "assistant settings"

    def __str__(self):
        return "Assistant settings"


class AssistantCommand(models.Model):
    """Knowledge written by shop admins. The assistant knows ONLY these entries (it cannot read the database)."""
    AUDIENCES = [("all", "Everyone"), ("customers", "Logged-in customers"), ("guests", "Guests")]
    trigger = models.SlugField(max_length=30, unique=True, help_text="Customers can type /trigger to get the exact reply, e.g. 'shipping'.")
    title = models.CharField(max_length=80, help_text="Shown on the quick-reply button.")
    response = models.TextField(max_length=1500, help_text="Exact reply for /trigger, and knowledge the AI may use in its own words.")
    keywords = models.CharField(max_length=200, blank=True, help_text="Comma separated. Used to pick this reply when the AI is switched off.")
    audience = models.CharField(max_length=10, choices=AUDIENCES, default="all")
    use_in_ai = models.BooleanField("Share with AI", default=True)
    show_chip = models.BooleanField("Show as quick button", default=True)
    active = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "trigger"]

    def __str__(self):
        return f"/{self.trigger}"

    def keyword_list(self):
        return [k.strip().lower() for k in self.keywords.split(",") if k.strip()]
