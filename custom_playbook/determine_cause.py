from robusta.api import *
from kubernetes import client, config
from datetime import datetime, timedelta

import logging

def need_more_memory(namespace, deployment_name):
    v1 = client.CoreV1Api()
    ret = v1.list_namespaced_pod(namespace=namespace)
    for i in ret.items:
        if i.metadata.labels.get('app') == deployment_name:
            for j in i.status.container_statuses:
                if j.last_state.terminated and j.last_state.terminated.reason == 'OOMKilled':
                    return True
    return False

def need_more_cpu(namespace, deployment_name):
    # either get cpu usage and compare it to cpu limit
    # or check log for obvious crashing reason
    return False

@action
def determine_cause(alert: PrometheusKubernetesAlert):
    # big question, what if dev has already manually scale up the resource?
    # and we need to have some sort of limitation on how many times should we trigger this
    try:
        config.load_kube_config()
    except:
        config.load_incluster_config()

    try:
        alert_subject = alert.get_alert_subject()
        subject_type = alert_subject.subject_type.value
        resource_name = alert_subject.name
        namespace = alert_subject.namespace
        if subject_type != "deployment":
            logging.info(f"skipping {resource_name} because its type is {subject_type}")

        if need_more_memory(namespace, resource_name):
            logging.info(f"{resource_name} is oomkilled, should increase memory")
            return

        if need_more_cpu(namespace, resource_name):
            logging.info(f"{resource_name} is crashing cause of the lack of cpu, should increase cpu")
            return

        logging.info(f"cannot automatically repair {resource_name}")
        return
    except Exception as e: print(e)

