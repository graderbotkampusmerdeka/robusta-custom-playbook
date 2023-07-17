from robusta.api import *
import logging

@action
def custom_action(alert: PrometheusKubernetesAlert):
    # we have full access to the pod on which the alert fired
    labels = alert.alert.labels
    if 'deployment' in labels:
        logging.info(f"[custom_action] executing custom_action for {labels['deployment']}")
    else:
        logging.info(f"[custom_action] executing custom_action for {labels}")

