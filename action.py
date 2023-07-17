from robusta.api import *
import logging

@action
def custom_action(event: PrometheusKubernetesAlert):
    # we have full access to the pod on which the alert fired
    pod = event.get_pod()
    pod_name = pod.metadata.name
    logging.info(f"[custom_action] executing custom_action for {pod_name}")
