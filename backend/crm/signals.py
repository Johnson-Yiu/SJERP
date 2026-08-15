from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Contact, Customer, Order, Quote


def refresh_customer_stage(customer_id):
    if not customer_id:
        return
    customer = Customer.objects.filter(pk=customer_id).first()
    if not customer:
        return

    order_count = customer.orders.exclude(status="cancelled").count()
    if order_count > 1:
        stage = "company"
    elif order_count == 1:
        stage = "customer"
    elif customer.quotes.exists():
        stage = "opportunity"
    elif customer.status == "contact" or customer.follow_ups.exclude(result="").exists():
        stage = "contact"
    else:
        stage = "lead"

    if customer.status != stage:
        Customer.objects.filter(pk=customer_id).update(status=stage)


@receiver(pre_save, sender=Quote)
@receiver(pre_save, sender=Order)
def remember_previous_customer(sender, instance, **kwargs):
    instance._previous_customer_id = None
    if instance.pk:
        instance._previous_customer_id = sender.objects.filter(pk=instance.pk).values_list("customer_id", flat=True).first()


@receiver(post_save, sender=Quote)
@receiver(post_save, sender=Order)
def update_customer_stage(sender, instance, **kwargs):
    refresh_customer_stage(instance.customer_id)
    previous_id = getattr(instance, "_previous_customer_id", None)
    if previous_id and previous_id != instance.customer_id:
        refresh_customer_stage(previous_id)


@receiver(post_delete, sender=Quote)
@receiver(post_delete, sender=Order)
def update_customer_stage_after_delete(sender, instance, **kwargs):
    refresh_customer_stage(instance.customer_id)


@receiver(post_delete, sender=Contact)
def promote_remaining_contact(sender, instance, **kwargs):
    if instance.is_primary:
        replacement = Contact.objects.filter(customer_id=instance.customer_id).order_by("created_at").first()
        if replacement:
            Contact.objects.filter(pk=replacement.pk).update(is_primary=True)
