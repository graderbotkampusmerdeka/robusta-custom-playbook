from robusta.api import *
import logging

@action
def determine_cause(alert: PrometheusKubernetesAlert):
    try:
        alert_subject = alert.get_alert_subject()
        logging.info(f"alert triggered for {alert_subject.subject_type.value} with name {alert_subject.name}")
        logging.info(f"need to find cause of termination of {alert_subject.name}")

    except Exception as e: print(e)

