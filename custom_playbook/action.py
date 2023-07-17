from robusta.api import *
import logging

@action
def custom_action(alert: PrometheusKubernetesAlert):
    alert_subject = alert.get_alert_subject()

    logging.info(f"[custom_action] executing custom_action for {alert_subject.subject_type.value} - {alert_subject.name}")

